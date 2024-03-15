# Debugging

When reporting a bug or posting questions to [issues](https://github.com/UniPiTechnology/evok/issues) please set logging levels in '/etc/evok/config.yaml' to DEBUG, restart your device and check the logs with command `journalctl -eu evok`. For more detailed log information you can also run evok by hand. To do that you need to first stop the service by executing the following command:

```bash
systemctl stop evok
```

Run evok manually by executing the following command:

```bash
/opt/evok/bin/evok -d
```

You can then examine or copy the output of the script.
