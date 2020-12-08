
;; Added by Package.el.  This must come before configurations of
;; installed packages.  Don't delete this line.  If you don't want it,
;; just comment it out by adding a semicolon to the start of the line.
;; You may delete these explanatory comments.
(package-initialize)

(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(ansi-color-faces-vector
   [default default default italic underline success warning error])
 '(ansi-color-names-vector
   ["#212526" "#ff4b4b" "#b4fa70" "#fce94f" "#729fcf" "#e090d7" "#8cc4ff" "#eeeeec"])
 '(custom-enabled-themes '(wheatgrass))
 '(desktop-load-default t)
 '(desktop-read t)
 '(desktop-restore-frames t)
 '(desktop-save-mode 1 nil (desktop))
 '(global-display-line-numbers-mode t)
 '(global-visual-line-mode t)
 '(package-selected-packages '(fountain-mode markdown-mode))
 '(save-place t nil (saveplace)))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )

(global-visual-line-mode 1)
(global-whitespace-mode 1)

(setq w32-use-visible-system-caret nil)

;; (global-set-key [(control ?h)] 'delete-backward-char)
;; (normal-erase-is-backspace-mode 1)

  (global-set-key [?\C-h] 'delete-backward-char)
  (global-set-key [?\C-x ?h] 'help-command)
                           ;; overrides mark-whole-buffer

(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/"))
