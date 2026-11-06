# MB1242 4-Sensor Sonar Array - ROS 2 Humble Driver

A complete ROS 2 integration package for reading a 4-sensor **MaxBotix I2CXL-MaxSonar-EZ (MB1242)** ultrasonic array via an **STM32 NUCLEO-F446RE** microcontroller and publishing distance measurements as a custom ROS 2 message on a single topic.

$$
\text{Raw Serial Stream: } [d_1, d_2, d_3, d_4] \quad (\text{cm}) \longrightarrow \text{ROS 2 Topic: } /sonar/ranges \quad [r_1, r_2, r_3, r_4] \quad (\text{m})
$$

---

## 1. System Architecture

```text
[MB1242 Sonar Array (S1..S4)]
           │  I2C1 (20 kHz Standard Mode, 4.7 kΩ pull-ups to 5 V)
           ▼
[STM32 NUCLEO-F446RE]
           │  Round-robin polling (~2.5 Hz total array sweep)
           │  USART2 ST-LINK USB @ 115200 Baud: "[d1, d2, d3, d4]\r\n"
           ▼
[/dev/ttyACM0 (Ubuntu 22.04 LTS / LattePanda Alpha)]
           │  mb1242_sonar node (Python 3 / PySerial)
           ▼
[ROS 2 Topic: /sonar/ranges]
           └── Type: mb1242_msgs/msg/SonarArray (r1, r2, r3, r4 as float32 in meters)
```

---

## 2. Repository Structure

This repository is designed to be cloned directly into your ROS 2 workspace's `src/` directory. It contains both the message interface package and the Python driver node:

```text
mb1242_ros2/
├── .gitignore
├── README.md
├── mb1242_msgs/                   # Custom ROS 2 Interface Package (ament_cmake)
│   ├── CMakeLists.txt
│   ├── package.xml
│   └── msg/
│       └── SonarArray.msg         # Custom message definition (float32 r1..r4)
└── mb1242_sonar/                  # Driver Node Package (ament_python)
    ├── package.xml
    ├── setup.cfg
    ├── setup.py
    └── mb1242_sonar/
        ├── __init__.py
        └── sonar_node.py          # Main ROS 2 serial parsing node
```

---

## 3. Host System Prerequisites (Ubuntu 22.04 LTS)

Run these setup steps once on any new Ubuntu machine before running the driver.

### 3.1 Disable ModemManager
Ubuntu's `ModemManager` service automatically probes newly connected USB serial devices, locking `/dev/ttyACM0` and causing PySerial read collisions. Disable it permanently:

```bash
sudo systemctl stop ModemManager.service
sudo systemctl disable ModemManager.service
```

### 3.2 Configure Persistent Serial Permissions
Grant your user permission to read and write to USB serial ports and add a persistent `udev` rule:

```bash
# Add current user to dialout group
sudo usermod -aG dialout $USER

# Set persistent 0666 permissions for all ACM and USB serial devices
echo 'KERNEL=="ttyACM*", MODE="0666"' | sudo tee /etc/udev/rules.d/99-serial.rules
echo 'KERNEL=="ttyUSB*", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-serial.rules

# Reload and apply udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Apply group changes to the current terminal session
newgrp dialout
```

### 3.3 Install ROS 2 Humble & Build Dependencies
If ROS 2 Humble is not already installed:

```bash
# Setup UTF-8 locale
sudo apt update && sudo apt install -y locales curl gnupg lsb-release software-properties-common
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Add ROS 2 repository
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS 2 Base, build tools, terminator, and pyserial
sudo apt update
sudo apt install -y ros-humble-ros-base python3-colcon-common-extensions python3-pip terminator
pip3 install pyserial
```

---

## 4. Git Setup: Cloning & Updating

### 4.1 Cloning on a New Machine
To port this setup to another device, create a workspace and clone the repository directly into `src`:

```bash
mkdir -p ~/sonar_ws/src
cd ~/sonar_ws/src
git clone <YOUR_GIT_REPOSITORY_URL> mb1242_ros2
```

### 4.2 Pulling Latest Updates
Whenever updates are pushed to the remote repository, pull the latest changes:

```bash
cd ~/sonar_ws/src/mb1242_ros2
git pull origin main
```

---

## 5. Building the Workspace

Always build the workspace from the root directory (`~/sonar_ws`):

```bash
cd ~/sonar_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
```

*Expected output:*
```text
Starting >>> mb1242_msgs
Finished <<< mb1242_msgs [X.XXs]
Starting >>> mb1242_sonar
Finished <<< mb1242_sonar [X.XXs]

Summary: 2 packages finished
```

### Automatic Sourcing (Recommended)
Add workspace sourcing to your `~/.bashrc` so that every new terminal tab or pane is ready automatically:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/sonar_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## 6. Execution & Verification

### Step 1: Identify the Serial Port
Connect the STM32 Nucleo USB cable to the host computer and verify the port assignment:

```bash
ls -l /dev/serial/by-id/
```

Look for the entry pointing to the ST-LINK interface (typically `/dev/ttyACM0` or `/dev/ttyACM1`):
```text
usb-STMicroelectronics_STM32_STLink_... -> ../../ttyACM0
```

### Step 2: Ensure Port is Free
If an old terminal session or monitor holds the port, free it:

```bash
sudo fuser -k /dev/ttyACM0
```

### Step 3: Launch the Driver Node
Run the node (pass `port:=/dev/ttyACM0` or your identified port):

```bash
cd ~/sonar_ws
source install/setup.bash
ros2 run mb1242_sonar sonar_node --ros-args -p port:=/dev/ttyACM0
```

*Expected Terminal Output:*
```text
[INFO] [mb1242_array_node]: Connected to STM32 on /dev/ttyACM0 @ 115200
```

### Step 4: Verify Topic in a Second Terminal
Open a new terminal or Terminator split pane (`Ctrl + Shift + O`), source your environment, and list active topics:

```bash
ros2 topic list
```

*Expected topics:*
```text
/parameter_events
/rosout
/sonar/ranges
```

### Step 5: Echo Live Range Measurements
Stream live readings:

```bash
ros2 topic echo /sonar/ranges
```

*Expected real-time output (readings in meters):*
```yaml
r1: 1.42
r2: 0.85
r3: 2.10
r4: 0.45
---
r1: 1.41
r2: 0.84
r3: 2.09
r4: 0.46
---
```

Wave your hand in front of each physical sensor:
* **Sensor 1** (`0xE0` on I2C) updates `r1`.
* **Sensor 2** (`0xE2` on I2C) updates `r2`.
* **Sensor 3** (`0xE4` on I2C) updates `r3`.
* **Sensor 4** (`0xE6` on I2C) updates `r4`.

---

## 7. Troubleshooting Matrix

| Problem | Root Cause | Solution |
| :--- | :--- | :--- |
| `[Errno 13] Permission denied: '/dev/ttyACM0'` | User lacks serial port permissions. | Run `sudo usermod -aG dialout $USER`, then run `newgrp dialout` or `sudo chmod 666 /dev/ttyACM0`. |
| `Serial parsing error: device reports readiness...` | Port contention from background process or ModemManager. | Run `sudo fuser -k /dev/ttyACM0` and disable ModemManager via `sudo systemctl disable --now ModemManager`. |
| `ModuleNotFoundError: No module named 'mb1242_msgs'` | Message package was not built or overlay was not sourced. | Run `cd ~/sonar_ws && colcon build --symlink-install && source install/setup.bash`. |
| `ModuleNotFoundError: No module named 'mb1242_sonar.sonar'` | Incorrect entry point format inside `setup.py`. | Ensure `setup.py` specifies `'sonar_node = mb1242_sonar.sonar_node:main'`. |
| Sensor distance outputs `0.0` continuously | The STM32 received an I2C NACK or sensor disconnected. | Check sensor power rail ($5\text{ V}$), GND bridge between Nucleo and sensors, and SDA/SCL pull-ups. |