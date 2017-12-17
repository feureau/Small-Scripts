# How to delete the commit history in github

from [Hellocoding](https://hellocoding.wordpress.com/2015/01/19/delete-all-commit-history-github/).

Sometimes you may find deleting the commit history of your github project repository useful. You can easily delete the commit history by following the procedure below.

It is always useful to keep the backup of your repository in your computer before removing all the commit history.

Let us start by cloning a github project. I am cloning ‘myproject’, you clone yours.

    $ git clone https://github.com/acsudeep/myproject.git

Since all the commit history are in the “.git” folder, we have to remove it. So, go inside your project folder. For me the project folder is ‘myproject’.

    $ cd myproject

And delete the ‘.git folder’ with this command.

    $ sudo rm -rf .git

Now, let us re-initialize the repository.

    $ git init

    $ git remote add origin https://github.com/acsudeep/myproject.git
    # add remote url

    $ git remote -v
    # verify

Next, let us add all our files and commit the changes.

    $ git add --all
    $ git commit -am 'initial commit'

Now, since we just have one commit i.e ‘initial commit’. Let us force push update to our master branch of our project repository.

    $ git push -f origin master

You may need to provide the credentials for your account.

Go and check your project repository in github, you should see only one commit.
