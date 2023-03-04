#! /bin/bash
REMOTE_HOST="hass"
SRCDIR="custom_components/kingspan_watchman_sensit"
for file in $SRCDIR/*.py $SRCDIR/manifest.json; do
  echo $(tput setaf 2)Copying $file$(tput sgr0)
  scp -q $file $REMOTE_HOST:/config/$SRCDIR
done
echo $(tput setaf 2)"Restarting HA Core"$(tput sgr0)
ssh $REMOTE_HOST "source /etc/profile.d/homeassistant.sh && ha core restart"
echo $(tput setaf 2)"Done"$(tput sgr0)
