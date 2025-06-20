#! /bin/bash
REMOTE_HOST="hass"
INTEGRATION_SRC_DIR="custom_components/kingspan_watchman_sensit"
INTEGRATION_SRC_FILES="__init__.py api.py config_flow.py const.py entity.py manifest.json sensor.py"
REMOTE_INTEGRATION_DIR="/config/custom_components/kingspan_watchman_sensit"
API_SRC_DIR="../kingspan-connect-sensor/src/connectsensor"
API_SRC_FILES="client.py debug.py exceptions.py tank.py"

if [ "$1" = "--api" ]; then
  USE_LOCAL_API=true
else
  USE_LOCAL_API=false
fi

function copy() {
  local src=$1
  local dest=$REMOTE_HOST:$2
  local dest_file="$2/$(basename $src)"

  if [ "$(basename $src)" == "manifest.json" ]; then
    echo "$(tput setaf 2)Patching:$(tput sgr0) manifest.json $(tput setaf 2)->$(tput sgr0) $dest_file"
    sed 's/"version": "\(.*\)"/"version": "0.0.1"/' $src | ssh $REMOTE_HOST "cat > $dest_file"
  else
    echo "$(tput setaf 2)Copy:$(tput sgr0) $src $(tput setaf 2)->$(tput sgr0) $dest"
    scp -q $src $dest
  fi
}

for file in $INTEGRATION_SRC_FILES; do
  copy $INTEGRATION_SRC_DIR/$file $REMOTE_INTEGRATION_DIR/
done

if [ $USE_LOCAL_API = "false" ]; then
  ssh hass "cd $REMOTE_INTEGRATION_DIR; rm -rf connectsensor"
else
  ssh hass mkdir -p $REMOTE_INTEGRATION_DIR/connectsensor
  for file in $API_SRC_FILES; do
    copy $API_SRC_DIR/$file $REMOTE_INTEGRATION_DIR/connectsensor/
  done
fi

copy $INTEGRATION_SRC_DIR/translations/en.json $REMOTE_INTEGRATION_DIR/translations

echo $(tput setaf 2)"Restarting HA Core"$(tput sgr0)
ssh $REMOTE_HOST "source /etc/profile.d/homeassistant.sh && ha core restart"
echo $(tput setaf 2)"Done"$(tput sgr0)
