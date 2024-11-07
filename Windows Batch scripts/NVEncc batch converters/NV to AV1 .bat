@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

NVEncC64 --avhw --codec av1 --tier 1 --profile high --crop 0,0,0,0 --qvbr 33 --preset p7 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --gop-len 12 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy -i %%A -o %%A_av1.mkv 

    mkdir AV1
    move %%A_av1.mkv  AV1\
)


COLOR 0A
PAUSE >nul
EXIT