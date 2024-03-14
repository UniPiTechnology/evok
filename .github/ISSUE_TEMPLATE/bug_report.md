---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

### Prerequisites

* [ ] Are you running the latest Main or the latest release version?
* [ ] Did you try to reinstall EVOK?
* [ ] Did you perform a cursory search on the [forum] and [google]?

### Log files needed

Set EVOK logging in "/etc/evok/config.yaml" to 'DEBUG'.
Include the output of the following commands on your device:

```
sudo su
ps -fax
journalctl -eu evok
```

### Description

[Description of the bug]

### Steps to Reproduce

1. [First Step]
2. [Second Step]
3. [and so on...]

**Expected behavior:** [What you expected to happen]

**Actual behavior:** [What actually happened]

[forum]:https://forum.unipi.technology/category/4/official-evok-api
[google]:http://www.google.com/
