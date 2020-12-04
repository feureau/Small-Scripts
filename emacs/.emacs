(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 ;; '(global-visual-line-mode t)
 '(desktop-enable t nil (desktop))
 '(save-place t nil (saveplace))
 '(desktop-load-default t)
 '(desktop-read t)
 '(global-display-line-numbers-mode t)
 '(ansi-color-faces-vector
   [default default default italic underline success warning error])
 '(ansi-color-names-vector
   ["#212526" "#ff4b4b" "#b4fa70" "#fce94f" "#729fcf" "#e090d7" "#8cc4ff" "#eeeeec"])
 '(custom-enabled-themes (quote (wheatgrass)))
 '(desktop-restore-frames t)
 '(desktop-save-mode 1)
 '(global-visual-line-mode t))
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
