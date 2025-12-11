startpg
-------

Are you concerned about the security of your shit?

- face - Frontend (webserver) process
- torso - Lib shared between face and hiney
- hiney - Backend (monitor, daemon) process

todo
----
- Dedupe www and https entries in yaml.  This:
```
        "-site":
          url: "http://site.example.net"
        "-sitewww":
          url: "http://www.site.example.net"
```
to this:
```
        "-site":
          url: "http://site.example.net"
          www: true
```
- Talk to opnsense and incorporate that DHCP data
