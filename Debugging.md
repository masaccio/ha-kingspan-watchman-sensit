# Debugging package dependencies

HomeAssistant installs dependencies using pip with a constraints file. The installer command is visible when HA is run with debug logs but if a dependency has mismatched constraints, errors are not clear:

``` text
2022-12-11 13:59:54.970 ERROR (SyncWorker_0) [homeassistant.util.package] Unable to install
package kingspan-connect-sensor>=2.0.4: ERROR: Cannot install kingspan-connect-sensor==2.0.4
because these package versions have conflicting dependencies.
```

This isn't picked up by poetry and `pytest-homeassistant-custom-component` but can be forced using:

``` bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install 'kingspan-connect-sensor>=2.0.4' --no-cache-dir \
    --upgrade --constraint package_constraints.txt \
    --find-links https://wheels.home-assistant.io/musllinux/ --prefer-binary
```

The constraints file is found at [package_constraints.txt](https://github.com/home-assistant/core/blob/dev/homeassistant/package_constraints.txt).
