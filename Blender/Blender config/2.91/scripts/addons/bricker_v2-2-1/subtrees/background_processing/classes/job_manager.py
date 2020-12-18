# Copyright (C) 2020 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# System imports
import os
import signal
import subprocess
import time
import json
import sys
import platform
import shlex

# Blender imports
import bpy
from bpy.types import Operator
from bpy.props import *

# Module imports
from ..functions import *


class JobManager():
    """ Manages and distributes jobs for all available workers """

    ################################################
    # initialization method

    def __init__(self):
        scn = bpy.context.scene
        # initialize vars
        self.temp_path = os.path.abspath(os.path.join(temp_path(), "background_processing"))
        self.jobs = list()
        self.passed_data = dict()
        self.uses_blend_file = dict()
        self.job_processes = dict()
        self.job_statuses = dict()
        self.job_paths = dict()
        self.job_timeouts = dict()
        self.retrieved_data = dict()
        self.stop_now = False
        self.blendfile_paths = dict()
        # create '/tmp/background_processing/' path if necessary
        if not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path)

    ###################################################
    # class variables

    instance = dict()
    max_workers = 5  # maximum number of blender instances to run at once
    max_attempts = 1  # maximum number of times the background processor will attempt to run a job if error occurs

    #############################################
    # class methods

    @staticmethod
    def get_instance(index=0):
        if index not in JobManager.instance:
            JobManager.instance[index] = JobManager()
        return JobManager.instance[index]

    def add_job(self, job:str, script:str, timeout:float=0, passed_data:dict=None, passed_data_blocks:set=None, use_blend_file:bool=False, overwrite_blend:bool=True):
        """
        Add a job to the job queue

        Keyword Arguments:
            job                -- job name
            script             -- path to the script to run in background
            timeout            -- job timeout in seconds; 0 for infinite
            passed_data        -- pass python data to the background script (dict entry key = variable name, dict entry value = value assigned to variable)
            passed_data_blocks -- pass blend data blocks to background scripts
            use_blend_file     -- run background script in a separate instance of the active blend file
            overwrite_blend    -- overwrite saved copy of the active blender file if running background script in instance of active blend file (does not overwrite active file itself)

        Returns:
            success       -- boolean if job successfully added to queue
            error message -- error message string if job not added to queue


        """
        # initialize empty parameters
        if passed_data is None:
            passed_data = dict()
        if passed_data_blocks is None:
            passed_data_blocks = set()
        # ensure blender file is saved
        if bpy.path.basename(bpy.data.filepath) == "":
            return False, "'bpy.data.filepath' is empty, please save the Blender file"
        # cleanup the job if it already exists
        if job in self.jobs:
            self.cleanup_job(job)
        # add job to the queue
        self.jobs.append(job)
        self.job_paths[job] = self.get_job_path(script, hash=job)
        self.blendfile_paths[job] = os.path.abspath(os.path.join(self.temp_path, bpy.path.basename(bpy.data.filepath)))
        self.passed_data[job] = passed_data
        self.uses_blend_file[job] = use_blend_file
        self.job_timeouts[job] = timeout
        self.job_statuses[job] = {"started":False, "returncode":None, "stdout":None, "stderr":None, "start_time":time.time(), "end_time":None, "attempts":0, "progress":0.0, "timed_out":False}
        # make image paths absolute
        old_filepaths = dict()
        for im in bpy.data.images:
            old_filepaths[im.name] = im.filepath
            im.filepath = bpy.path.abspath(im.filepath)
        # send passed_data_blocks to library file
        sent_data_blocks_path = os.path.join(self.temp_path, job + "_sent_data.blend")
        if len(passed_data_blocks) > 0:
            bpy.data.libraries.write(sent_data_blocks_path, passed_data_blocks, fake_user=True)
        # save the active blend file to be used in Blender instance
        if use_blend_file and (not os.path.exists(self.blendfile_paths[job]) or overwrite_blend):
            try:
                # save the file to new location
                bpy.ops.wm.save_as_mainfile(filepath=self.blendfile_paths[job], relative_remap=False, compress=False, copy=True)
            except RuntimeError as e:
                if not str(e).startswith("Error: Unable to pack file"):
                    return False, e
        # reset image paths
        for im in bpy.data.images:
            im.filepath = old_filepaths[im.name]
        # insert final blend file name to top of files
        target_path_base = os.path.join(self.temp_path, job)
        # clear old files if they exist
        progress_file_path = target_path_base + "_progress.py"
        blend_data_file_path = target_path_base + "_retrieved_data.blend"
        python_data_file_path = target_path_base + "_retrieved_data.py"
        for f in (progress_file_path, blend_data_file_path, python_data_file_path):
            if os.path.isfile(f):
                os.remove(f)
        # add storage path and additional passed data to lines in job file in READ mode
        lines = add_lines(script, target_path_base, self.passed_data[job], sent_data_blocks_path)
        # write text to job file in WRITE mode
        src=open(self.job_paths[job],"w")
        src.writelines(lines)
        src.close()
        return True, ""

    def start_job(self, job:str, debug_level:int=0):
        """ Start a job in the job queue """
        # send job string to background blender instance with subprocess
        binary_path = bpy.app.binary_path
        blendfile_path = "'" + self.blendfile_paths[job] + "'" if self.uses_blend_file[job] else ""
        temp_job_path = self.job_paths[job]
        # TODO: Choose a better exit code than 155
        thread_func = "'%(binary_path)s' %(blendfile_path)s -b --python-exit-code 155 -P '%(temp_job_path)s'" % locals()
        if platform.system() not in ("Darwin", "Linux"):
            thread_func = shlex.split(thread_func)
        self.job_processes[job] = subprocess.Popen(thread_func, stdout=subprocess.PIPE if debug_level in (0, 2) and platform.system() in ("Darwin", "Linux") else None, stderr=subprocess.PIPE if debug_level < 2 and platform.system() in ("Darwin", "Linux") else None, shell=True)
        self.job_statuses[job]["started"] = True
        self.job_statuses[job]["start_time"] = time.time()
        self.job_statuses[job]["attempts"] += 1
        self.retrieved_data[job] = {"retrieved_data_blocks":None, "retrieved_python_data":None}
        print("JOB STARTED:  ", job)

    def process_job(self, job:str, debug_level:int=0, overwrite_data=False):
        # check if job has been started
        if not self.job_started(job) or (self.job_statuses[job]["returncode"] not in (None, 0) and self.job_statuses[job]["attempts"] < self.max_attempts):
            # start job if background worker available
            if len(self.job_processes) < self.max_workers:
                self.start_job(job, debug_level=debug_level)
            return
        job_status = self.job_statuses[job]
        # check if job already processed
        if job_status["returncode"] is not None:
            return
        # check if job has exceeded the time limit
        elif self.job_timeouts[job] > 0 and time.time() - job_status["start_time"] > self.job_timeouts[job]:
            self.kill_job(job)
            self.job_statuses[job]["timed_out"] = True
        job_process = self.job_processes[job]
        job_process.poll()
        # check if job process still running
        if job_process.returncode is None:
            self.update_job_progress(job)
        else:
            self.job_processes.pop(job)
            # record status of completed job process
            job_status["end_time"] = time.time()
            job_status["returncode"] = job_process.returncode
            stdout_lines = tuple() if job_process.stdout is None else job_process.stdout.readlines()
            stderr_lines = tuple() if job_process.stderr is None else job_process.stderr.readlines()
            job_status["stdout"] = [line.decode("ASCII")[:-1] for line in stdout_lines]
            job_status["stderr"] = [line.decode("ASCII")[:-1] for line in stderr_lines]
            # if job was successful, retrieve any saved blend data
            if job_status["returncode"] == 0:
                try:
                    self.retrieve_data(job, overwrite_data)
                except FileNotFoundError as e:
                    job_status["returncode"] = -42
                    job_status["stderr"] = ["EXCEPTION (<class 'FileNotFoundError'>): No data file found by 'retrieve_data()' function", "", str(e)]
            # print status of job
            print("JOB CANCELLED:" if job_status["returncode"] != 0 else "JOB ENDED:    ", job, " (returncode:" + str(job_status["returncode"]) + ")" if job_status["returncode"] != 0 else "(time elapsed:" + get_elapsed_time(job_status["start_time"], job_status["end_time"]) + ")")

    def process_jobs(self):
        for job in self.jobs:
            if self.jobs_complete():
                break
            self.process_job(job)

    def update_job_progress(self, job:str):
        progress_file_path = os.path.join(self.temp_path, "%(job)s_progress.py" % locals())
        if not os.path.exists(progress_file_path): return
        progress_file = open(progress_file_path, "r")
        progress = progress_file.readline()
        progress_file.close()
        if progress == "": return
        self.job_statuses[job]["progress"] = float(progress)

    def retrieve_data(self, job:str, overwrite_data:bool=False):
        # retrieve python data stored to temp directory
        data_file_path = os.path.join(self.temp_path, "%(job)s_retrieved_data.py" % locals())
        data_file = open(data_file_path, "r")
        dumped_dict = data_file.readline()
        data_file.close()
        self.retrieved_data[job]["retrieved_python_data"] = marshal.loads(bytes.fromhex(dumped_dict)) if dumped_dict != "" else {}
        # retrieve blend data stored to temp directory
        full_blend_path = os.path.join(self.temp_path, "%(job)s_retrieved_data.blend" % locals())
        orig_data_names = lambda: None
        with bpy.data.libraries.load(full_blend_path) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))
                # store copies of loaded attributes to 'orig_data_names' object
                if overwrite_data:
                    attrib = getattr(data_from, attr)
                    if len(attrib) > 0:
                        setattr(orig_data_names, attr, attrib.copy())
        # overwrite existing data with loaded data of the same name
        if overwrite_data:
            for attr in dir(orig_data_names):
                # bypass lambda function attributes
                if attr.startswith("__"): continue
                # get attributes to remap
                source_attr = getattr(orig_data_names, attr)
                target_attr = getattr(data_to, attr)
                for i, data_name in enumerate(source_attr):
                    # check that the data doesn't match
                    if not hasattr(target_attr[i], "name") or target_attr[i].name == data_name or not hasattr(bpy.data, attr): continue
                    # remap existing data to loaded data
                    data_attr = getattr(bpy.data, attr)
                    data_attr.get(data_name).user_remap(target_attr[i])
                    # remove remapped existing data
                    data_attr.remove(data_attr.get(data_name))
                    # rename loaded data to original name
                    target_attr[i].name = data_name
        self.retrieved_data[job]["retrieved_data_blocks"] = data_to

    def get_job_path(self, script:str, hash:str):
        job_name = os.path.basename(script)
        name, ext = os.path.splitext(job_name)
        new_job_name = "{name}_{hash}{ext}".format(name=name, hash=hash, ext=ext)
        return os.path.join(self.temp_path, new_job_name)

    def get_job_names(self):
        return self.jobs

    def get_queued_job_names(self):
        return [job for job in self.jobs if not self.job_started(job)]

    def get_active_job_names(self):
        return [job for job in self.jobs if self.job_started(job) and not (self.job_complete(job) or self.job_dropped(job))]

    def get_completed_job_names(self):
        return [job for job in self.jobs if self.job_complete(job)]

    def get_dropped_job_names(self):
        return [job for job in self.jobs if self.job_dropped(job)]

    def get_job_state(self, job:str):
        if not self.job_started(job):
            return "QUEUED"
        elif self.job_complete(job):
            return "COMPLETED"
        elif self.job_dropped(job):
            return "DROPPED"
        else:
            return "ACTIVE"

    def get_job_progress(self, job:str):
        return self.job_statuses[job]["progress"]

    def get_retrieved_python_data(self, job:str):
        return self.retrieved_data[job]["retrieved_python_data"]

    def get_retrieved_data_blocks(self, job:str):
        return self.retrieved_data[job]["retrieved_data_blocks"]

    def get_issue_string(self, job:str):
        if not self.job_dropped(job): return ""
        if self.job_timed_out(job):
            errormsg = "\nJob '%(job)s' timed out\n\n" % locals()
        else:
            errormsg = "\n------ ISSUE WITH BACKGROUND PROCESSOR ------\n\n"
            stderr = self.job_statuses[job]["stderr"]
            stdout = self.job_statuses[job]["stdout"]
            errormsg += "[stderr]\n" if len(stderr) > 0 else "[stdout]\n"
            for line in stderr if len(stderr) > 0 else stdout:
                if line.startswith("\r"):
                    errormsg = errormsg[:last_msg_len]
                last_msg_len = len(errormsg)
                errormsg += line + "\n"
            errormsg += "\n---------------------------------------------\n"
        return errormsg

    def job_started(self, job:str):
        return self.job_statuses[job]["started"]

    def job_complete(self, job:str):
        """ returns True if job was completed successfully (return code 0) """
        return self.job_statuses[job]["returncode"] == 0

    def job_dropped(self, job:str):
        """ returns True if job was killed, timed out, or encountered an error """
        return self.job_statuses[job]["attempts"] == self.max_attempts and self.job_statuses[job]["returncode"] not in (None, 0)

    def job_killed(self, job:str):
        """ returns True if job was killed or timed out """
        return self.job_statuses[job]["returncode"] == -9

    def job_timed_out(self, job:str):
        """ returns True if job timed out """
        return self.job_statuses[job]["timed_out"] and self.job_statuses[job]["attempts"] == self.max_attempts

    def jobs_complete(self):
        for job in self.jobs:
            if not self.job_complete(job):
                return False
        return True

    def kill_job(self, job:str):
        p = self.job_processes[job]
        if platform.system() == "Windows":
            # os.kill(p.pid, signal.CTRL_C_EVENT)
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(self.job_processes[job].pid)])  # causes CPU issues
        else:
            self.job_processes[job].kill()

    def kill_all(self):
        for job in self.jobs.copy():
            self.cleanup_job(job)

    def cleanup_job(self, job):
        """ removes job from all JobManager data structures """
        assert job in self.jobs
        self.jobs.remove(job)
        del self.passed_data[job]
        if job in self.job_processes:
            self.kill_job(job)
            del self.job_processes[job]
        if job in self.job_statuses:
            del self.job_statuses[job]
        if job in self.retrieved_data:
            del self.retrieved_data[job]

    def num_available_workers(self):
        return self.max_workers - len(self.job_processes)

    def num_pending_jobs(self):
        return len([status for status in self.job_statuses.values() if not status["started"]])

    def num_running_jobs(self):
        return len(self.job_processes)

    def num_completed_jobs(self):
        return len(self.get_completed_job_names())

    def num_dropped_jobs(self):
        return len(self.get_dropped_job_names())

    ###################################################
