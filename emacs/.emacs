(setq gnutls-algorithm-priority "NORMAL:-VERS-TLS1.3")
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(ansi-color-faces-vector
   [default default default italic underline success warning error])
 '(ansi-color-names-vector
   ["#212526" "#ff4b4b" "#b4fa70" "#fce94f" "#729fcf" "#e090d7" "#8cc4ff" "#eeeeec"])
 '(custom-enabled-themes '(material))
 '(custom-safe-themes
   '("7922b14d8971cce37ddb5e487dbc18da5444c47f766178e5a4e72f90437c0711" "89885317e7136d4e86fb842605d47d8329320f0326b62efa236e63ed4be23c58" default))
 '(desktop-enable t nil (desktop))
 '(desktop-load-default t)
 '(desktop-read t)
 '(desktop-restore-frames t)
 '(desktop-save-mode 1)
 '(global-auto-revert-mode t)
 '(global-visual-line-mode t)
 '(global-whitespace-mode t)
 '(package-selected-packages
   '(sentence-navigation visual-fill-column pdf-tools material-theme flycheck better-defaults fountain-mode elpy))
 '(save-place t nil (saveplace)))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )



(setq w32-use-visible-system-caret nil)

;; (global-set-key [(control ?h)] 'delete-backward-char)
;; (normal-erase-is-backspace-mode 1)

(global-set-key [?\C-h] 'delete-backward-char)
(global-set-key [?\M-h] 'backward-kill-word)
;;(global-set-key [?\C-x ?h] 'help-command)
                           ;; overrides mark-whole-buffer

(require 'package)
  (add-to-list
   'package-archives
   ;; '("melpa" . "http://stable.melpa.org/packages/") ; many packages won't show if using stable
   '("melpa" . "https://melpa.org/packages/"))
(put 'downcase-region 'disabled nil)
(put 'upcase-region 'disabled nil)


 ;;; Stefan Monnier <foo at acm.org>. It is the opposite of fill-paragraph    
    (defun unfill-paragraph (&optional region)
      "Takes a multi-line paragraph and makes it into a single line of text."
      (interactive (progn (barf-if-buffer-read-only) '(t)))
      (let ((fill-column (point-max))
            ;; This would override `fill-column' if it's an integer.
            (emacs-lisp-docstring-fill-column t))
        (fill-paragraph nil region)))

  ;; Handy key definition
    (define-key global-map "\M-Q" 'unfill-paragraph)
;; .emacs.d/init.el

;; ===================================
;; MELPA Package Support
;; ===================================
;; Enables basic packaging support
(require 'package)

;; Adds the Melpa archive to the list of available repositories
(add-to-list 'package-archives
             '("melpa" . "http://melpa.org/packages/") t)

;; Initializes the package infrastructure
(package-initialize)

;; If there are no archived package contents, refresh them
(when (not package-archive-contents)
  (package-refresh-contents))

;; Installs packages
;;
;; myPackages contains a list of package names
(defvar myPackages
  '(better-defaults                 ;; Set up some better Emacs defaults
    elpy                            ;; Emacs Lisp Python Environment
    flycheck                        ;; On the fly syntax checking
    py-autopep8                     ;; Run autopep8 on save
    blacken                         ;; Black formatting on save
    material-theme                  ;; Theme
    sentence-navigation             ;; emacs sentence navigation
    fast-scroll
    beacon
    olivetti
    fountain-mode
    centered-cursor-mode
    )
  )

;; Scans the list in myPackages
;; If the package listed is not already installed, install it
(mapc #'(lambda (package)
          (unless (package-installed-p package)
            (package-install package)))
      myPackages)

;; ===================================
;; Basic Customization
;; ===================================

(setq inhibit-startup-message t)    ;; Hide the startup message
(load-theme 'material t)            ;; Load material theme
(global-linum-mode t)               ;; Enable line numbers globally
;; ====================================
;; Development Setup
;; ====================================
;; Enable elpy
(elpy-enable)

;; Enable Flycheck
(when (require 'flycheck nil t)
  (setq elpy-modules (delq 'elpy-module-flymake elpy-modules))
  (add-hook 'elpy-mode-hook 'flycheck-mode))

;; Enable autopep8
(require 'py-autopep8)
(add-hook 'elpy-mode-hook 'py-autopep8-enable-on-save)

;; User-Defined init.el ends here

;;; auto-save-buffers-enhanced.el --- Automatically save buffers in a decent way
;; -*- coding: utf-8; mode:emacs-lisp -*-

;; Copyright (C) 2007 Kentaro Kuribayashi
;; Author: Kentaro Kuribayashi <kentarok@gmail.com>
;; Note  : auto-save-buffers-enhanced.el borrows main ideas and some
;;         codes written by Satoru Takabayashi and enhances original
;;         one. Thanks a lot!!!
;;         See http://0xcc.net/misc/auto-save/

;; This file is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published
;; by the Free Software Foundation; either version 2, or (at your
;; option) any later version.

;; This file is distributed in the hope that it will be useful, but
;; WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
;; General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with GNU Emacs; see the file COPYING.  If not, write to the
;; Free Software Foundation, Inc., 59 Temple Place - Suite 330,
;; Boston, MA 02111-1307, USA.

;;; Commentary:

;; * Description
;;
;; Emacs's native auto-save feature simply
;; sucks. auto-save-buffers-enhanced.el provides such and other more
;; useful features which only require a few configurations to set up.
;;
;; auto-save-buffers-enhanced.el borrows main ideas and some codes
;; written by Satoru Takabayashi and enhances the original one. Thanks
;; a lot!!!
;;
;; See http://0xcc.net/misc/auto-save/
;;
;; * Usage
;;
;; Just simply put the code below into your .emacs:
;;
;;   (require 'auto-save-buffers-enhanced)
;;   (auto-save-buffers-enhanced t)
;;
;; You can explicitly set what kind of files should or should not be
;; auto-saved. Pass a list of regexps like below:
;;
;;   (setq auto-save-buffers-enhanced-include-regexps '(".+"))
;;   (setq auto-save-buffers-enhanced-exclude-regexps '("^not-save-file" "\\.ignore$"))
;;
;; If you want `auto-save-buffers-enhanced' to work only with the files under
;; the directories checked out from VCS such as CVS, Subversion, and
;; svk, put the code below into your .emacs:
;;
;;   ;; If you're using CVS or Subversion or git
;;   (require 'auto-save-buffers-enhanced)
;;   (auto-save-buffers-enhanced-include-only-checkout-path t)
;;   (auto-save-buffers-enhanced t)
;;
;;   ;; If you're using also svk
;;   (require 'auto-save-buffers-enhanced)
;;   (setq auto-save-buffers-enhanced-use-svk-flag t)
;;   (auto-save-buffers-enhanced-include-only-checkout-path t)
;;   (auto-save-buffers-enhanced t)
;;
;; You can toggle `auto-save-buffers-enhanced' activity to execute
;; `auto-save-buffers-enhanced-toggle-activity'. For convinience, you
;; might want to set keyboard shortcut of the command like below:
;;
;;   (global-set-key "\C-xas" 'auto-save-buffers-enhanced-toggle-activity)
;;
;; Make sure that you must reload the SVK checkout paths from your
;; configuration file such as `~/.svk/config', in which SVK stores the
;; information on checkout paths, by executing
;; `auto-save-buffers-reload-svk' after you check new files out from
;; your local repository. You can set a keyboard shortcut for it like
;; below:
;;
;;   (global-set-key "\C-xar" 'auto-save-buffers-enhanced-reload-svk)
;;
;; For more details about customizing, see the section below:
;;

;;; Change Log:

;; 2011-08-01:
;;  * added a feature; auto-save *scratch* buffer into file.
;;
;; 2008-03-14:
;;  * fixed a typo: s/activitiy/avtivity/
;;
;; 2008-02-22:
;;  * fixed a bug: auto-saving didn't work under unreasonable situation...
;;    (Thanks to typester)
;;
;; 2008-02-19:
;;  * added git support.
;;  * fixed a bug: this package didn't work with SVN and CVS if
;;    use-svk-flag is non-nil.
;;
;; 2007-12-10:
;;  * added a command, `auto-save-buffers-enhanced-reload-svk'.
;;    (Thanks to typester: http://unknownplace.org/memo/2007/12/10#e001)
;;
;; 2007-10-18:
;;  * initial release

;;; Code:

;;;; You can customize auto-save-buffers-enhanced via the variables below
;;;; -------------------------------------------------------------------------

(defvar auto-save-buffers-enhanced-interval 0.5
  "*Interval by the second.

For that time, `auto-save-buffers-enhanced-save-buffers' is in
idle")

(defvar auto-save-buffers-enhanced-include-regexps '(".+")
  "*List that contains regexps which match `buffer-file-name' to
be auto-saved.")

(defvar auto-save-buffers-enhanced-exclude-regexps nil
  "*List that contains regexps which match `buffer-file-name' not
to be auto-saved.")

(defvar auto-save-buffers-enhanced-use-svk-flag nil
  "*If non-nil, `auto-save-buffers-enhanced' recognizes you're using svk
not CVS or Subversion.")

(defvar auto-save-buffers-enhanced-svk-config-path "~/.svk/config"
  "*Path of the config file of svk, which is usually located in
~/.svk/config.")

(defvar auto-save-buffers-enhanced-quiet-save-p nil
  "*If non-nil, without 'Wrote <filename>' message.")

(defvar auto-save-buffers-enhanced-save-scratch-buffer-to-file-p nil
  "*If non-nil, *scratch* buffer will be saved into the file same
as other normal files.")

(defvar auto-save-buffers-enhanced-cooperate-elscreen-p nil
  "*If non-nil, insert scratch data to elscreen default window.")

(defvar auto-save-buffers-enhanced-file-related-with-scratch-buffer
  (expand-file-name "~/.scratch")
  "*File which scratch buffer to be save into.")

;;;; Imprementation Starts from Here...
;;;; -------------------------------------------------------------------------

(eval-when-compile
 (require 'cl))

(defvar auto-save-buffers-enhanced-activity-flag t
  "*If non-nil, `auto-save-buffers-enhanced' saves buffers.")

;;;###autoload
(defun auto-save-buffers-enhanced (flag)
  "If `flag' is non-nil, activate `auto-save-buffers-enhanced' and start
auto-saving."
  (when flag
    (run-with-idle-timer
     auto-save-buffers-enhanced-interval t 'auto-save-buffers-enhanced-save-buffers))
  (when auto-save-buffers-enhanced-save-scratch-buffer-to-file-p
    (add-hook 'after-init-hook 'auto-save-buffers-enhanced-scratch-read-after-init-hook))
  (when auto-save-buffers-enhanced-cooperate-elscreen-p
    (add-hook 'elscreen-create-hook 'auto-save-buffers-enhanced-cooperate-elscreen-default-window)))

(defun auto-save-buffers-enhanced-scratch-read-after-init-hook ()
  (let ((scratch-buf (get-buffer "*scratch*")))
    (when (and scratch-buf
               (file-exists-p auto-save-buffers-enhanced-file-related-with-scratch-buffer))
      (with-current-buffer scratch-buf
        (erase-buffer)
        (insert-file-contents auto-save-buffers-enhanced-file-related-with-scratch-buffer)))))

(defalias 'auto-save-buffers-enhanced-cooperate-elscreen-default-window
  'auto-save-buffers-enhanced-scratch-read-after-init-hook)

;;;###autoload
(defun auto-save-buffers-enhanced-include-only-checkout-path (flag)
  "If `flag' is non-nil, `auto-save-buffers-enhanced' saves only
the directories under VCS."
  (when flag
    (progn
      (setq auto-save-buffers-enhanced-include-regexps nil)
      (when auto-save-buffers-enhanced-use-svk-flag
        (auto-save-buffers-enhanced-add-svk-checkout-path-into-include-regexps))
      (add-hook 'find-file-hook
                'auto-save-buffers-enhanced-add-checkout-path-into-include-regexps))))

;;;; Command
;;;; -------------------------------------------------------------------------

;;;###autoload
(defun auto-save-buffers-enhanced-toggle-activity ()
  "Toggle `auto-save-buffers-enhanced' activity"
  (interactive)
  (if auto-save-buffers-enhanced-activity-flag
      (setq auto-save-buffers-enhanced-activity-flag nil)
    (setq auto-save-buffers-enhanced-activity-flag t))
  (if auto-save-buffers-enhanced-activity-flag
      (message "auto-save-buffers-enhanced on")
    (message "auto-save-buffers-enhanced off")))

;;;###autoload
(defun auto-save-buffers-enhanced-reload-svk ()
  "Reload the checkout paths from SVK configuration file."
  (interactive)
  (auto-save-buffers-enhanced-add-svk-checkout-path-into-include-regexps)
  (message (format "Realoaded checkout paths from %s" auto-save-buffers-enhanced-svk-config-path)))

;;;; Main Function
;;;; -------------------------------------------------------------------------

(defun auto-save-buffers-enhanced-save-buffers ()
  "Save buffers if `buffer-file-name' matches one of
`auto-save-buffers-enhanced-include-regexps' and doesn't match
`auto-save-buffers-enhanced-exclude-regexps'."
  (save-current-buffer
    (dolist (buffer (buffer-list))
      (set-buffer buffer)
      (if (and buffer-file-name
               auto-save-buffers-enhanced-activity-flag
               (buffer-modified-p)
               (not buffer-read-only)
               (auto-save-buffers-enhanced-regexps-match-p
                auto-save-buffers-enhanced-include-regexps buffer-file-name)
               (not (auto-save-buffers-enhanced-regexps-match-p
                     auto-save-buffers-enhanced-exclude-regexps buffer-file-name))
               (file-writable-p buffer-file-name))
          (auto-save-buffers-enhanced-saver-buffer)
        (when (and auto-save-buffers-enhanced-save-scratch-buffer-to-file-p
                   (equal buffer (get-buffer "*scratch*"))
                   (buffer-modified-p)
                   (not (string= initial-scratch-message (buffer-string))))
          (auto-save-buffers-enhanced-saver-buffer 'scratch))))))

;;;; Internal Functions
;;;; -------------------------------------------------------------------------

(defun auto-save-buffers-enhanced-saver-buffer (&optional scratch-p)
  (cond
   (scratch-p
    (let
        ((content (buffer-string)))
      (with-temp-file
          auto-save-buffers-enhanced-file-related-with-scratch-buffer
        (insert content))
      (set-buffer-modified-p nil)))
   (auto-save-buffers-enhanced-quiet-save-p
    (auto-save-buffers-enhanced-quiet-save-buffer))
   (t (save-buffer))))

(defun auto-save-buffers-enhanced-quiet-save-buffer ()
  (fset 'original-write-region (symbol-function 'write-region))
  (flet
      ((write-region (start end filename &optional append visit lockname mustbenew)
                     (original-write-region start end filename append -1 lockname mustbenew))
       (message (format-string &rest args) t))
    (save-buffer)
    (set-buffer-modified-p nil)
    (clear-visited-file-modtime)))

(defun auto-save-buffers-enhanced-regexps-match-p (regexps string)
  (catch 'matched
    (dolist (regexp regexps)
      (if (string-match regexp string)
          (throw 'matched t)))))

(defun auto-save-buffers-enhanced-add-svk-checkout-path-into-include-regexps ()
  (save-current-buffer
    (find-file auto-save-buffers-enhanced-svk-config-path)
    (when (file-readable-p buffer-file-name)
      (toggle-read-only))
    (goto-char (point-min))
    (while (re-search-forward "^[\t ]+\\(\\(/[^\n]+\\)+\\):[ ]*$" nil t)
      (when (and (file-exists-p (match-string 1))
                 (not (memq (match-string 1) auto-save-buffers-enhanced-include-regexps)))
        (setq auto-save-buffers-enhanced-include-regexps
              (cons (concat "^" (regexp-quote (match-string 1)))
                    auto-save-buffers-enhanced-include-regexps))))
    (kill-buffer (current-buffer))))

(defun auto-save-buffers-enhanced-add-checkout-path-into-include-regexps ()
  (let ((current-dir default-directory)
        (checkout-path nil))
    (catch 'root
      (while t
        (if (or (file-exists-p ".svn")
                (file-exists-p ".cvs")
                (file-exists-p ".git"))
            (setq checkout-path (expand-file-name default-directory)))
        (cd "..")
        (when (equal "/" default-directory)
            (throw 'root t))))
    (when (and checkout-path
               (not (memq checkout-path auto-save-buffers-enhanced-include-regexps)))
      (setq auto-save-buffers-enhanced-include-regexps
            (cons (concat "^" (regexp-quote checkout-path))
                  auto-save-buffers-enhanced-include-regexps)))
    (cd current-dir)))

(provide 'auto-save-buffers-enhanced)

;;; auto-save-buffers-enhanced.el ends here


(require 'auto-save-buffers-enhanced)
(auto-save-buffers-enhanced t)

(load "auctex.el" nil t t)
(setq TeX-auto-save t)
(setq TeX-parse-self t)
(setq-default TeX-master nil)

(add-to-list 'load-path "E:\\GitHub\\twauctex\\")
(require 'twauctex)
(twauctex-global-mode)


(global-set-key (kbd "M-e") 'sentence-nav-forward)
(global-set-key (kbd "M-a") 'sentence-nav-backward)


(defun p2l ()
  "Format current paragraph into single lines."
  (interactive "*")
  (save-excursion
    (forward-paragraph)
    (let ((foo (point)))
      (backward-paragraph)
      (replace-regexp "\n" " " nil (1+ (point)) foo)
      (backward-paragraph)
      (replace-regexp "\\. ?" ".\n" nil (point) foo))))


(global-set-key (kbd "M-q") 'p2l)
(global-set-key (kbd "C-q") 'unfill-paragraph)

(require 'centered-cursor-mode)
(centered-cursor-mode t)
(flyspell-mode t)
(global-hl-line-mode t)
