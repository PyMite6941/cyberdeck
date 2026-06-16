# cyberdeck shell theme — sourced from ~/.bashrc (line added by setup.sh).
# Edit freely; changes apply on next shell. Keep it POSIX-ish bash.

# ── prompt: ┌─[user@deck]─[~/path]  (green/cyan, red ✗ on failed command) ──
__deck_prompt() {
    local exit=$?
    local G='\[\e[1;32m\]' C='\[\e[1;36m\]' R='\[\e[1;31m\]' X='\[\e[0m\]'
    local status=""
    [[ $exit -ne 0 ]] && status="${R}✗${exit} "
    PS1="${G}┌─[${C}\u@\h${G}]─[${C}\w${G}]\n└─${status}${G}▶${X} "
}
PROMPT_COMMAND=__deck_prompt

# ── aliases & helpers ──
alias ls='ls --color=auto'
alias ll='ls -lah --color=auto'
alias bootlog='cat /var/log/cyberdeck-boot.log'
alias deck='cd /opt/cyberdeck'
alias mem='free -h'

# RAM-saving modes: deck-lite drops to console (frees ~500 MB — use before
# heavy local-LLM runs), deck-gui restores the desktop. Survives reboot.
deck-lite() {
    sudo systemctl set-default multi-user.target
    sudo systemctl isolate multi-user.target
}
deck-gui() {
    sudo systemctl set-default graphical.target
    sudo systemctl isolate graphical.target
}

# SoC temperature in °C — vcgencmd on Pi (4 and 5), sysfs fallback anywhere else.
temp() {
    if command -v vcgencmd >/dev/null 2>&1; then
        vcgencmd measure_temp | cut -d= -f2
    elif [[ -r /sys/class/thermal/thermal_zone0/temp ]]; then
        awk '{printf "%.1f'\''C\n", $1/1000}' /sys/class/thermal/thermal_zone0/temp
    else
        echo "n/a"
    fi
}

# ── greet interactive SSH/terminal sessions with system info ──
if [[ $- == *i* ]] && command -v fastfetch >/dev/null 2>&1; then
    # Only once per session, not for every subshell
    if [[ -z ${DECK_GREETED:-} ]]; then
        export DECK_GREETED=1
        fastfetch --config /opt/cyberdeck/fastfetch.jsonc 2>/dev/null \
            || fastfetch 2>/dev/null || true
    fi
fi

# ── auto-resume deck-ide after isolation ──
# deck-ide writes ~/.deck-ide-pending before calling 'systemctl isolate'.
# On the next VT login (login shell, not already inside tmux), we pick it up
# and drop straight into the IDE session.
if [[ -o login ]] && [[ -z "${TMUX:-}" ]] && [[ -f "$HOME/.deck-ide-pending" ]]; then
    rm -f "$HOME/.deck-ide-pending"
    if command -v deck-ide >/dev/null 2>&1; then
        sleep 0.3  # let systemd finish settling after isolation
        exec deck-ide
    fi
fi
