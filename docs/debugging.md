# Debugging


When reporting a bug or posting questions to [our forum] please set proper logging levels in '/etc/evok/config.yaml',
restart your device and check the logs with command `journalctl -eu evok`.
For more detailed log information you can also run evok by hand.
To do that you need to first stop the service by executing the following command:

```bash
systemctl stop evok
```

Run evok manually by executing the following command:

```bash
/opt/evok/bin/evok -d
```

You can then look through/paste the output of the script.

## Developer Note

Do you feel like contributing to EVOK, or perhaps have a neat idea for an improvement to our system? Great! We are open to all ideas. Get in touch with us via email to info at unipi DOT technology
