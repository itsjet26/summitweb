#!/bin/bash

bash start_facefusion.sh &
bash start_video_retalker.sh &
bash start_rvc.sh &
bash start_program3.sh &

sleep 15

bash startup_dashboard.sh
