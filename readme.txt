Patrick Welch

War server and client

This program serves as both client and server for the card game war over a local network.
The program is operated using command line arguments.

The first argument can be 'server', 'client' or 'clients' to determine the behavior
of the instance.

The second and third arguments provide the ip address and listening port, respectively.

The option 4th argument is required when 'clients' is used and provides a way to spawn 
multiple client instances form one terminal.

Examples:

 python war.py server 127.0.0.1 4444

 python war.py client 127.0.0.1 4444
 
 python war.py clients 127.0.0.1 4444 500