;====================================================
;;twauctex
;====================================================
;(add-to-list 'load-path (expand-file-name "~//"))
;(require 'twauctex)
;(twauctex-global-mode)
				       


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

;;=====================================
;;"Format current paragraph into single lines."
;;===========================================

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
    real-auto-save 
    fountain-mode
    centered-cursor-mode
    visual-fill-column
    sentence-navigation
    real-auto-save
    stripe-buffer
    saveplace
    use-package
    ;;auctex
    wc-mode
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
(setq-default fill-column 30)

(setq auto-fill-mode t)

(setq inhibit-startup-message t)    ;; Hide the startup message
;;(load-theme 'material t)            ;; Load material theme
;; (global-linum-mode t)               ;; Enable line numbers globally
(global-display-line-numbers-mode t) ;; You can disable linum-mode and use display-line-numbers-mode instead which is part of Emacs since version 26 and scales well when increasing font size.
(global-visual-line-mode t)

;; autosave every 1 seconds
(require 'real-auto-save)
(add-hook 'prog-mode-hook 'real-auto-save-mode)
(setq real-auto-save-interval 1) ;; in seconds

;;(global-flycheck-mode t)
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
 '(custom-enabled-themes '(material))
 '(custom-safe-themes
   '("90a6f96a4665a6a56e36dec873a15cbedf761c51ec08dd993d6604e32dd45940" "f149d9986497e8877e0bd1981d1bef8c8a6d35be7d82cba193ad7e46f0989f6a" default))
 '(display-line-numbers-major-tick 0)
 '(fci-rule-color "#37474f")
 '(global-display-line-numbers-mode t)
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
 '(default ((t (:family "DejaVu Sans Mono" :foundry "PfEd" :slant normal :weight normal :height 143 :width normal))))
 '(mode-line ((t (:height 0.5)))))


 
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
