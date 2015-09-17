#!/bin/bash

source settings/ccb_api_login_info.bash

curl 'https://ingomar.ccbchurch.com/api.php?srv=update_individual&individual_id=5' -u $CCB_API_USERNAME:$CCB_API_PASSWORD -d'sync_id=X534YW1DW'
