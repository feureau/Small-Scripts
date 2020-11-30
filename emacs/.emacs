(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(cursor-type 'box)
 '(custom-enabled-themes '(wheatgrass)))
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
  (global-set-key [?\C-x ?h] 'help-command)
                           ;; overrides mark-whole-buffer
