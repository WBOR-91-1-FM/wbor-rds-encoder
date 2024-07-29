import subprocess


def initiate_netcat_connection(host, port):
    try:
        return subprocess.Popen(
            ["nc", host, str(port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
    except FileNotFoundError:
        print("Netcat (nc) is not installed or not found in the system.")
        return None


def send_command_over_netcat(nc_process, command):
    try:
        nc_process.stdin.write(command.encode() + b"\n")
        nc_process.stdin.flush()
        output = nc_process.stdout.readline().decode().strip()
        print(output)
    except Exception as e:
        print(f"Error sending Netcat command: {e}")


if __name__ == "__main__":
    host = ""
    port = 1025

    nc_process = initiate_netcat_connection(host, port)
    if nc_process:
        while True:
            command = input("Enter a command to send (type 'exit' to quit): ")
            if command.lower() == "exit":
                break
            send_command_over_netcat(nc_process, command)
