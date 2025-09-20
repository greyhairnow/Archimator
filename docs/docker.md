# Running Archimator in Docker

This project ships with a container image definition that bundles the GUI client
and its Python dependencies. The container can be used for reproducible builds
or when you want an isolated environment with the correct system libraries for
Tkinter, PyMuPDF and Pillow.

> **Important:** The GUI rendering still requires an X server on the host. On
> Linux this can be your native X11 session. On Windows or macOS install an X
> server (e.g. Xming, VcXsrv or XQuartz) and expose it to the container.

## Build the image

```bash
docker build -t archimator .
```

The Dockerfile installs the packages listed in `app/src/app/requirements.txt`
and the Linux libraries that the GUI stack needs.

## Run the GUI (Linux example)

```bash
# Allow the container (root user) to talk to your X server
xhost +si:localuser:root

# Launch the GUI using your host DISPLAY and X11 socket
DISPLAY=${DISPLAY:-:0} \
docker run --rm \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  archimator
```

You can mount additional volumes if you want to persist exported CSV files or
load PDFs stored outside the container, for example:

```bash
docker run --rm \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$PWD/data":/workspace/data \
  archimator
```

## Using docker-compose

A `docker-compose.yml` file is provided for convenience:

```bash
xhost +si:localuser:root
docker compose up --build gui
```

You can override the command or mount extra volumes by extending the compose
file in your local environment.

## Windows & macOS notes

1. Install an X server (VcXsrv/Xming on Windows, XQuartz on macOS) and ensure it
   allows TCP/X11 connections from Docker containers.
2. Set the `DISPLAY` environment variable to point at your host server
   (`host.docker.internal:0` on Windows/macOS when the X server listens on TCP).
3. When the X server requires TCP, remove the `/tmp/.X11-unix` bind and open the
   appropriate port instead, e.g. `-p 6000:6000`.
4. WSL2 users running Docker Desktop can export their display to the Windows X
   server with `export DISPLAY=$(grep -m1 nameserver /etc/resolv.conf | awk '{print $2}'):0`.

## Headless usage

The application is a Tkinter GUI; running it in a container without an X server
will exit immediately. If you need automated workflows (e.g. export CSV without
rendering), consider creating a CLI entry point that does not require Tkinter
and reusing the same base image.
