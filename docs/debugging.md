# Debugging

When reporting a bug or posting questions to [issues](https://github.com/UniPiTechnology/evok/issues) please set logging levels in `/etc/evok/config.yaml` to `DEBUG`, restart your device and check the logs with command `journalctl -eu evok`. For more detailed log information you can also run Evok manually. In order to do that, you need to stop its service first.

```bash title="Stopping Evok service"
systemctl stop evok
```

```bash title="Running Evok manually"
/opt/evok/bin/evok -d
```

You can examine or copy the output.
