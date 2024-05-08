;====================================================
;;twauctex
;====================================================
;(add-to-list 'load-path (expand-file-name "~//"))
;(require 'twauctex)
;(twauctex-global-mode)
				       

;====================================================
;; hunspell
;====================================================

(setq ispell-program-name "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell")

;; Set $DICPATH to "$HOME/Library/Spelling" for hunspell.

(setenv "DICPATH" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell")

;; Tell ispell-mode to use hunspell.
(setq ispell-program-name "hunspell")

(setq-default ispell-hunspell-dict-paths-alist
	      '(
		("default" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\default.aff")
		("en_US" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\en_US.aff")
		("de_DE" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\de_DE.aff")
		("de_CH" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\de-CH.aff")
		("en_GB" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\en_GB.aff")
		("en_US" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\en_US.aff")
		("id_ID" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\id_ID.aff")
		("nl_NL" "C:\\Users\\Feureau\\AppData\\Roaming\\Hunspell\\share\\hunspell\\nl_NL.aff")
		))

(with-eval-after-load "ispell"
  ;; Configure `LANG`, otherwise ispell.el cannot find a 'default
  ;; dictionary' even though multiple dictionaries will be configured
  ;; in next line.
  (setenv "LANG" "en_US.UTF-8")
  (setq ispell-program-name "hunspell")
  ;; Configure German, Swiss German, and two variants of English.
  (setq ispell-dictionary "de_DE,de_CH,en_GB,en_US,id_ID,nl_NL")
  ;; ispell-set-spellchecker-params has to be called
  ;; before ispell-hunspell-add-multi-dic will work
  (ispell-set-spellchecker-params)
  (ispell-hunspell-add-multi-dic "de_DE,de_CH,en_GB,en_US,id_ID,nl_NL")
  ;; For saving words to the personal dictionary, don't infer it from
  ;; the locale, otherwise it would save to ~/.hunspell_de_DE.
  (setq ispell-personal-dictionary "~/.hunspell_personal"))

;; The personal dictionary file has to exist, otherwise hunspell will
;; silently not use it.
;(unless (file-exists-p ispell-personal-dictionary)
;  (write-region "" nil ispell-personal-dictionary nil 0))

;; It works!  It works!  After two hours of slogging, it works!
;;(if (file-exists-p "/usr/bin/hunspell")
    ;;(progn
      ;;(setq ispell-program-name "hunspell")
      ;;(eval-after-load "ispell"
      ;;'(progn (defun ispell-get-coding-system () 'utf-8)))))

;=============================================
; unfill paragraph
;==========================================

    ;;; Stefan Monnier <foo at acm.org>. It is the opposite of fill-paragraph    
    (defun unfill-paragraph (&optional region)
      "Takes a multi-line paragraph and makes it into a single line of text."
      (interactive (progn (barf-if-buffer-read-only) '(t)))
      (let ((fill-column (point-max))
            ;; This would override `fill-column' if it's an integer.
            (emacs-lisp-docstring-fill-column t))
        (fill-paragraph nil region)))
    
    ;; Handy key definition
;;    (define-key global-map "/C-Q" 'unfill-paragraph)
      (global-set-key [?\C-Q] 'unfill-paragraph)

;=============================================
;fix ctrl-h
;============================================

(global-set-key [?\C-h] 'delete-backward-char)
(global-set-key [?\M-h] 'backward-kill-word)
;;(global-set-key [?\C-x ?h] 'help-command) ;; overrides mark-whole-buff

;; =====================================
;; "Format current paragraph into single lines."
;; ===========================================

(defun paragraph-single-line ()
  "Format current paragraph into single lines."
  (interactive "*")
  (save-excursion
    (forward-paragraph)
    (let ((foo (point)))
      (backward-paragraph)
      (replace-regexp "\n" " " nil (1+ (point)) foo)
      (backward-paragraph)
      (replace-regexp "\\. ?" ".\n" nil (point) foo))))

(global-set-key (kbd "M-Q") 'paragraph-single-line)

(global-set-key (kbd "C-M-Q") 'just-one-space)

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

;; load .el files in the folder
;;(add-to-list 'load-path "~/.emacs.d/lisp/")

;; Installs packages
;;
;; myPackages contains a list of package names
(defvar myPackages
  '(better-defaults                 ;; Set up some better Emacs defaults
    material-theme                  ;; Theme
    fountain-mode
    centered-cursor-mode
    ;;visual-fill-column
    sentence-navigation
    real-auto-save
    stripe-buffer
    saveplace
    use-package
    auctex
    wc-mode
    topspace
    ;;flymake-markdownlint
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

(set-face-attribute 'mode-line nil  :height 5)
(setq wc-mode t)
(setq wc-idle-wait 2)


(setq auto-fill-mode t)

(setq inhibit-startup-message t)    ;; Hide the startup message
;;(load-theme 'material t)            ;; Load material theme
;; (global-linum-mode t)               ;; Enable line numbers globally
(global-display-line-numbers-mode t) ;; You can disable linum-mode and use display-line-numbers-mode instead which is part of Emacs since version 26 and scales well when increasing font size.
(global-visual-line-mode t)
; (global-flycheck-mode t)
(auto-save-visited-mode t)
(global-hl-line-mode t)
(flyspell-mode t)
(desktop-save-mode t)

;; User-Defined init.el ends here
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(ansi-color-faces-vector
   [default default default italic underline success warning error])
 '(ansi-color-names-vector
   ["#212526" "#ff4b4b" "#b4fa70" "#fce94f" "#729fcf" "#e090d7" "#8cc4ff" "#eeeeec"])
 '(custom-enabled-themes '(modus-vivendi))
 '(custom-safe-themes
   '("90a6f96a4665a6a56e36dec873a15cbedf761c51ec08dd993d6604e32dd45940" "f149d9986497e8877e0bd1981d1bef8c8a6d35be7d82cba193ad7e46f0989f6a" default))
 '(display-line-numbers-major-tick 0)
 '(fci-rule-color "#37474f")
 '(flycheck-checker-error-threshold 40000000)
 '(hl-sexp-background-color "#1c1f26")
 '(package-selected-packages
   '(stripe-buffer material-theme string-inflection sentence-navigation py-autopep8 olivetti markdown-mode fountain-mode flycheck fast-scroll elpy centered-cursor-mode blacken better-defaults beacon auctex))
 '(vc-annotate-background nil)
 '(vc-annotate-color-map
   '((20 . "#f36c60")
     (40 . "#ff9800")
     (60 . "#fff59d")
     (80 . "#8bc34a")
     (100 . "#81d4fa")
     (120 . "#4dd0e1")
     (140 . "#b39ddb")
     (160 . "#f36c60")
     (180 . "#ff9800")
     (200 . "#fff59d")
     (220 . "#8bc34a")
     (240 . "#81d4fa")
     (260 . "#4dd0e1")
     (280 . "#b39ddb")
     (300 . "#f36c60")
     (320 . "#ff9800")
     (340 . "#fff59d")
     (360 . "#8bc34a")))
 '(vc-annotate-very-old-color nil))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(default ((t (:family "DejaVu Sans Mono" :foundry "outline" :slant normal :weight normal :height 181 :width normal))))
 '(fringe ((t (:background "black"))))
 '(mode-line ((t (:height 0.5)))))



;; ======================================
;; visual fill column mode
;; this soft wraps text at 80 and centers the text
;; ======================================

;;(add-hook 'visual-line-mode-hook #'visual-fill-column-mode)

;; (setq-default visual-fill-column-center-text t)

;;(setq-default fill-column 80)

;======================================
;real-auto-save settings
;======================================

(require 'real-auto-save)
(add-hook 'prog-mode-hook 'real-auto-save-mode)
(setq real-auto-save-interval 1) ;; in seconds

					;=============================
; save position in buffer
;============================
(use-package saveplace
  :init (save-place-mode))



;; Scroll window

(defface sync-window-face ;; originally copied from font-lock-function-name-face
  '((((class color) (min-colors 88) (background light)) (:foreground "Yellow" :background "Blue1"))
    (((class color) (min-colors 88) (background dark)) (:foreground "Red" :background  "LightSkyBlue"))
    (((class color) (min-colors 16) (background light)) (:foreground "Blue" :background "Yellow"))
    (((class color) (min-colors 16) (background dark)) (:foreground "LightSkyBlue" :background "Yellow"))
    (((class color) (min-colors 8)) (:foreground "blue" :bold t))
    (t (:bold t)))
  "Face used to highlight regions in `sync-window-mode' slaves."
  :group 'sync-window)

(defvar sync-window-overlay nil
  "Overlay for current master region in `sync-window-mode' slaves.")
(make-variable-buffer-local 'sync-window-overlay)

(defun sync-window-cleanup ()
  "Clean up after `sync-window-mode'."
  (interactive)
  (if (overlayp sync-window-overlay)
      (progn
    (delete-overlay sync-window-overlay)
    (setq sync-window-overlay nil))
    (remove-overlays (point-min) (point-max) 'sync-window-slave t)))

(defvar sync-window-master-hook nil
  "Hooks to be run by `sync-window' in the master window ")

(defun sync-window (&optional display-start)
  "Synchronize point position other window in current frame.
Only works if there are exactly two windows in the active wrame not counting the minibuffer."
  (interactive)
  (when (= (count-windows 'noMiniBuf) 2)
    (let ((p (line-number-at-pos))
      (start (line-number-at-pos (or display-start (window-start))))
      (vscroll (window-vscroll))
      breg ereg)
      (when (use-region-p)
    (setq breg (line-number-at-pos (region-beginning))
          ereg  (line-number-at-pos (if (looking-back "\n") (1- (region-end)) (region-end)))))
      (run-hooks 'sync-window-master-hook)
      (other-window 1)
      (goto-char (point-min))
      (when breg
    (sync-window-cleanup)
    (overlay-put (setq sync-window-overlay (make-overlay (line-beginning-position breg) (line-end-position ereg))) 'face 'sync-window-face)
    (overlay-put sync-window-overlay 'sync-window-slave t))
      (setq start (line-beginning-position start))
      (forward-line (1- p))
      (set-window-start (selected-window) start)
      (set-window-vscroll (selected-window) vscroll)
      (other-window 1)
      (unless display-start
    (redisplay t))
      )))

(defvar sync-window-mode-hook nil
  "Hooks to be run at start of `sync-window-mode'.")

(define-minor-mode sync-window-mode
  "Synchronized view of two buffers in two side-by-side windows."
  :group 'windows
  :lighter " ⇕"
  (if sync-window-mode
      (progn
    (add-hook 'post-command-hook 'sync-window-wrapper 'append t)
    (add-to-list 'window-scroll-functions 'sync-window-wrapper)
    (run-hooks 'sync-window-mode-hook)
    (sync-window))
    (remove-hook 'post-command-hook 'sync-window-wrapper t)
    (setq window-scroll-functions (remove 'sync-window-wrapper window-scroll-functions))
    ))

(defun sync-window-wrapper (&optional window display-start)
  "This wrapper makes sure that `sync-window' is fired from `post-command-hook'
only when the buffer of the active window is in `sync-window-mode'."
  (with-selected-window (or window (selected-window))
    (when sync-window-mode
      (sync-window display-start))))

(provide 'sync-window)


;; ===========================
;; https://abizjak.github.io/emacs/2016/03/06/latex-fill-paragraph.html
;; ===========================

;; (defun ales/fill-paragraph (&optional P)
;;   "When called with prefix argument call `fill-paragraph'.
;; Otherwise split the current paragraph into one sentence per line."
;;   (interactive "P")
;;   (if (not P)
;;       (save-excursion 
;;         (let ((fill-column 12345678)) ;; relies on dynamic binding
;;           (fill-paragraph) ;; this will not work correctly if the paragraph is
;;                            ;; longer than 12345678 characters (in which case the
;;                            ;; file must be at least 12MB long. This is unlikely.)
;;           (let ((end (save-excursion
;;                        (forward-paragraph 1)
;;                        (backward-sentence)
;;                        (point-marker))))  ;; remember where to stop
;;             (beginning-of-line)
;;             (while (progn (forward-sentence)
;;                           (<= (point) (marker-position end)))
;;               (just-one-space) ;; leaves only one space, point is after it
;;               (delete-char -1) ;; delete the space
;;               (newline)        ;; and insert a newline
;;               (LaTeX-indent-line) ;; I only use this in combination with late, so this makes sense
;;               ))))
;;     ;; otherwise do ordinary fill paragraph
;;     (fill-paragraph P)))


;; (define-key LaTeX-mode-map (kbd "M-q") 'ales/fill-paragraph)



;; =========================================
;; ospl-mode
;; =========================================

;;; ospl-mode.el --- One Sentence Per Line Mode

;; Copyright (C) 2018 Christian Dietrich
;; Copyright (C) 2015 Scot Weldon
;; Copyright (C) 2014 Franceso

;; Author: Christian Dietrich <stettberger@dokucode.de>
;; URL: https://github.com/stettberger/ospl-mode.el
;; Version: 1.0
;; Keywords: line break, ospl
;; Package-Requires: ((visual-fill-column "1.9"))

;;; Commentary:
;; see https://emacs.stackexchange.com/questions/443/editing-files-with-one-sentence-per-line

;;; Code:

(defgroup ospl nil
  "One Sentence Per Line Mode."
  :prefix "ospl-"
  :group 'visual-line)


(defcustom ospl-adaptive-wrap-prefix t
  "Enable adaptive-wrap-prefix-mode with OSPL mode."
  :type 'boolean
  :group 'ospl)

(require 'visual-fill-column)

(defun ospl/unfill-paragraph ()
  "Unfill the paragraph at point.
This repeatedly calls `join-line' until the whole paragraph does
not contain hard line breaks any more."
  (let ((fill-column 100000))
    (fill-paragraph)))


(defun ospl/fill-paragraph ()
  "Fill the current paragraph until there is one sentence per line.
This unfills the paragraph, and places hard line breaks after each sentence."
  (interactive)
  (save-excursion
    (fill-paragraph)
    (ospl/unfill-paragraph)  ; remove hard line breaks
    (beginning-of-line)

    ;; insert line breaks again
    (let ((end-of-paragraph (make-marker)))
      (set-marker end-of-paragraph (line-end-position))
      (forward-sentence)
      (while (< (point) end-of-paragraph)
        (just-one-space)
        (delete-backward-char 1)
        (newline)
        (forward-sentence))
      (set-marker end-of-paragraph nil))))

(defvar-local ospl/old-modes nil)

(defun ospl/push-mode (mode &optional enabled)
  "Save the state of an old mode."
  (add-to-list 'ospl/old-modes
               (cons mode (if (eq enabled nil)
                              (if (boundp mode) (symbol-value mode) -1)
                            enabled))))

(defun ospl/pop-mode (mode)
  "Get the state of an old mode."
  (if (alist-get mode ospl/old-modes) 1 -1))

(defun ospl/update-margin ()
  "Update the fill margins"
  ;; This is an ugly hack, until visual-fill-column gets fixed
  (visual-fill-column-mode -1)
  (visual-fill-column-mode 1)
  (set-window-buffer nil (current-window)))


;;;###autoload
(define-minor-mode ospl-mode
  "One Sentence Per Line"
  :init-value nil
  :lighter " ospl"
  :keymap (let ((map (make-sparse-keymap)))
            (define-key map (kbd "M-q") 'ospl/fill-paragraph)
            map)

  (if ospl-mode
      (progn
        (add-hook 'text-scale-mode-hook #'ospl/update-margin)
        (add-hook 'window-size-change-functions  'ospl/update-margin)
        ;; Enable visual-line-mode
        (ospl/push-mode 'visual-line-mode)
        (visual-line-mode 1)
        ;; Enable Visual-Fill-Column-Mode
        (ospl/push-mode 'visual-fill-column-mode)
        (visual-fill-column-mode 1)
        ;; Disable auto-fill-mode, as it really conflicts
        (ospl/push-mode 'auto-fill-mode
                        (not (eq auto-fill-function nil)))
        (auto-fill-mode -1)
        ;; Adaptive Wrap for nicer wrapping
        (when ospl-adaptive-wrap-prefix
          (require 'adaptive-wrap)
          (ospl/push-mode 'adaptive-wrap-prefix-mode)
          (adaptive-wrap-prefix-mode 1)
          (setq adaptive-wrap-extra-indent 2))
        )
    (progn
      (remove-hook 'text-scale-mode-hook #'ospl/update-margin)
      (remove-hook 'window-size-change-functions  'ospl/update-margin)
      (visual-line-mode (ospl/pop-mode 'visual-line-mode))
      (visual-fill-column-mode (ospl/pop-mode 'visual-fill-column-mode))
      (auto-fill-mode (ospl/pop-mode 'auto-fill-mode))
      (if ospl-adaptive-wrap-prefix
          (adaptive-wrap-prefix-mode (ospl/pop-mode 'adpative-wrap-prefix-mode)))
      ;; (setq ospl/old-modes nil)
      )))

(provide 'ospl-mode)

;;; ospl-mode.el ends here

(use-package ospl-mode
  :hook (TeX-mode . ospl-mode))

;; =================================
;; Enable spellcheck by default
;; ===================================

(add-hook 'text-mode-hook 'flyspell-mode)
(add-hook 'prog-mode-hook 'flyspell-prog-mode)


;; ====== fringe ======

;; A small minor mode to use a big fringe
(defvar bzg-big-fringe-mode nil)
(define-minor-mode bzg-big-fringe-mode
  "Minor mode to use big fringe in the current buffer."
  :init-value nil
  :global t
  :variable bzg-big-fringe-mode
  :group 'editing-basics
  (if (not bzg-big-fringe-mode)
      (set-fringe-style nil)
    (set-fringe-mode
     (/ (- (frame-pixel-width)
           (* 100 (frame-char-width)))
        2))))

;; Now activate this global minor mode
(bzg-big-fringe-mode 1)

;; To activate the fringe by default and deactivate it when windows
;; are split vertically, uncomment this:
;; (add-hook 'window-configuration-change-hook
;;           (lambda ()
;;             (if (delq nil
;;                       (let ((fw (frame-width)))
;;                         (mapcar (lambda(w) (< (window-width w) (/ fw 2)))
;;                                 (window-list))))
;;                 (bzg-big-fringe-mode 0)
;;               (bzg-big-fringe-mode 1))))

;; Use a minimal cursor
;; (setq default-cursor-type 'hbar)

;; Get rid of the indicators in the fringe
(mapcar (lambda(fb) (set-fringe-bitmap-face fb 'org-hide))
        fringe-bitmaps)


;; ===== turn off light - all dark =====
;; https://bzg.fr/en/emacs-strip-tease/#sec-6


