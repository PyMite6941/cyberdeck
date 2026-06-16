#!/usr/bin/env bash
# cyberdeck login banner — installed to /etc/update-motd.d/10-cyberdeck.
# Shown on every console/SSH login. Pure bash + standard tools, no deps.

G='\e[1;32m'; C='\e[1;36m'; D='\e[2;32m'; R='\e[1;31m'; Y='\e[1;33m'; X='\e[0m'

printf "${G}"
cat <<'BANNER'
    ____  ______________
   / __ \/ ____/ ____/ __ \
  / / / / /_  / /   / / / /
 / /_/ / __/ / /___/ /_/ /
/_____/_/   \____/_____/   cyberdeck
BANNER
printf "${X}"

ip=$(hostname -I 2>/dev/null | awk '{print $1}')
disk=$(df -h / 2>/dev/null | awk 'NR==2{print $3" / "$2" ("$5")"}')
mem=$(free -h 2>/dev/null | awk 'NR==2{print $3" / "$2}')
swap=$(free -h 2>/dev/null | awk 'NR==3{print $3" / "$2}')
up=$(uptime -p 2>/dev/null | sed 's/^up //')

# Temp via vcgencmd (Pi 4 & 5), sysfs fallback; coloured green/yellow/red.
temp=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2)
if [[ -z $temp && -r /sys/class/thermal/thermal_zone0/temp ]]; then
    temp=$(awk '{printf "%.1f'\''C", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
fi
tc=$G
tnum=${temp%%.*}
tnum=${tnum%%[^0-9]*}
if [[ $tnum =~ ^[0-9]+$ ]]; then
    (( tnum >= 75 )) && tc=$R || { (( tnum >= 65 )) && tc=$Y; }
fi

# Throttled indicator: show ⚠ if the Pi is being throttled or under-voltage.
throttled=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
throttle_warn=""
if [[ -n $throttled && $throttled != "0x0" ]]; then
    throttle_warn="${R} ⚠${X}"
fi

printf "${D}──────────────────────────────────────────${X}\n"
printf " ${C}host${X}   %s\n" "$(hostname)"
printf " ${D}tip${X}    ${D}run 'deck-help' for all commands${X}\n"
printf " ${C}ip${X}     %s\n" "${ip:-offline}"
 printf " ${C}temp${X}   ${tc}%s${X}%s\n" "${temp:-n/a}" "$throttle_warn"
printf " ${C}mem${X}    %s\n" "${mem:-n/a}"
printf " ${C}swap${X}   %s (zram)\n" "${swap:-n/a}"
printf " ${C}disk${X}   %s\n" "${disk:-n/a}"
printf " ${C}up${X}     %s\n" "${up:-n/a}${throttle_warn}"
printf "${D}──────────────────────────────────────────${X}\n"
