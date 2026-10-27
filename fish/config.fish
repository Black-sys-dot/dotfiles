source /usr/share/cachyos-fish-config/cachyos-config.fish

# overwrite greeting
# potentially disabling fastfetch
#function fish_greeting
#    # smth smth
#end


# Added by Antigravity CLI installer
set -gx PATH "/home/black/.local/bin" $PATH

# Two-column fetch with per-line icons (overrides the CachyOS greeting above)
function fish_greeting
    ~/.config/fastfetch/fetch.py
end
