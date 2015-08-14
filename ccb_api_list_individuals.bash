#!/bin/bash

source settings/ccb_api_login_info.bash

curl 'https://ingomar.ccbchurch.com/api.php?srv=individual_profiles' -u user:pwd -u $CCB_API_USERNAME:$CCB_API_PASSWORD
