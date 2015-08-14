#!/bin/bash

source settings/ccb_api_login_info.bash

curl 'https://ingomar.ccbchurch.com/api.php?srv=create_group' -u $CCB_API_USERNAME:$CCB_API_PASSWORD -d'name=DELETE_ANDYF&main_leader_id=5&interaction_type=Announce+Only'
