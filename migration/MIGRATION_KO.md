# FR3 작업 환경 이전 가이드 (기존 노트북 → 새 노트북)

작성: 2026-10-07. 기존 노트북(HP OMEN, Ubuntu 22.04.5, 커널 6.8.0-138-generic, ROS2 Humble)에서 실제로 동작한 구성을 그대로 재현하는 순서다.

## 0. 새 노트북 전제 조건

- Ubuntu 22.04 + ROS2 Humble (`/opt/ros/humble`). 다른 Ubuntu/ROS 버전이면 이 가이드를 그대로 쓰지 말 것.
- 유선 이더넷 포트(내장 또는 USB-이더넷). Control Box C2(Shop Floor 포트)에 직결한다.
- RT 커널은 필수 아님(기존 노트북도 일반 커널). 다만 기존 노트북에서 bringup abort(-6)가 2회 있었고 원인 미확정.

## 1. 저장소 구성

GitHub 비공개 저장소: https://github.com/yezin293/franka_ros2_ws

| 경로 | 내용 |
|---|---|
| fr3.repos | 원본 패키지 4개(libfranka 0.15.0, franka_ros2 v2.0.2, franka_description 1.0.1, olvx c3444ed) 주소와 버전 |
| migration/franka_ros2_local_changes.patch | franka_ros2 v2.0.2에 대한 수정 5개 (controllers.yaml, move_group.launch.py, moveit.rviz, franka_semantic_components/CMakeLists.txt, 새 fr3_arm_controller_real.yaml) |
| src/fr3_skills/ | 우리가 만든 동작 패키지 (move_home) |
| scripts/ | small_joint_move.py |
| CLAUDE_HANDOFF_KO.md 등 문서 | 진행 기록 (Claude는 CLAUDE_HANDOFF_KO.md부터 읽는다) |

원본 패키지와 build/install/log는 저장소에 없다(.gitignore). 아래 2~3단계로 만든다.

## 2. 저장소 받기 (새 컴퓨터에서 처음 한 번)

clone 하면 그 시점 최신 내용을 모두 받으므로 clone 직후 git pull은 필요 없다.

```bash
git clone https://github.com/yezin293/franka_ros2_ws.git ~/franka_ros2_ws
```

```bash
cd ~/franka_ros2_ws
```

## 3. 원본 패키지 받기와 패치 적용 (처음 한 번)

vcs 명령이 없으면 먼저 설치:

```bash
sudo apt install python3-vcstool
```

fr3.repos에 적힌 버전으로 원본 패키지 4개를 src/에 받는다:

```bash
vcs import --recursive src < fr3.repos
```

franka_ros2에 우리 수정사항 적용:

```bash
git -C src/franka_ros2 apply ../../migration/franka_ros2_local_changes.patch
```

```bash
git -C src/franka_ros2 status --short
```

수정(M) 4개 + 새 파일(??) 1개가 보이면 정상.

## 4. 의존성 설치와 빌드

```bash
cd ~/franka_ros2_ws
```

```bash
source /opt/ros/humble/setup.bash
```

```bash
rosdep install --from-paths src --ignore-src -r -y
```

기존 노트북에 설치돼 있던 주요 패키지(누락 시 설치): ros-humble-desktop, MoveIt2(ros-humble-moveit), ros-humble-ros2-control, ros-humble-ros2-controllers(joint_trajectory_controller 포함), ros-humble-pinocchio.

```bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

## 5. 실시간 우선순위 권한 (rtprio)

`/etc/security/limits.d/99-franka-research.conf` 파일을 아래 내용으로 만든다. 사용자 이름은 새 노트북 계정으로 바꾼다.

```text
<사용자이름> soft rtprio 99
<사용자이름> hard rtprio 99
```

로그아웃 후 다시 로그인하고 확인 (99가 나와야 함):

```bash
ulimit -r
```

## 6. 로봇 연결 네트워크

이더넷 인터페이스 이름 확인 (기존 노트북은 enp129s0):

```bash
ip -br link
```

아래 `<인터페이스>`를 위에서 확인한 이름으로 바꿔 실행. 기존 노트북과 같은 설정(고정 IP, 기본 경로 없음, IPv6 끔)이다.

```bash
nmcli connection add type ethernet ifname <인터페이스> con-name franka-direct ipv4.method manual ipv4.addresses 172.16.0.10/24 ipv4.never-default yes ipv6.method disabled connection.autoconnect yes connection.autoconnect-priority 100
```

케이블을 C2에 꽂은 뒤 확인:

```bash
ping -c3 172.16.0.2
```

브라우저에서 Desk: https://172.16.0.2/desk/

## 7. 동작 확인 순서

1. fake hardware로 먼저 확인 (로봇 불필요):

```bash
ros2 launch franka_bringup franka.launch.py arm_id:=fr3 use_fake_hardware:=true load_gripper:=false
```

2. 그다음 실물: CLAUDE_HANDOFF_KO.md의 "운영 규칙"과 터미널1~3 순서를 따른다 (bringup → spawner --inactive → move_group execute:=true → 움직이기 직전 activate → 끝나면 deactivate).

## 8. 기존 노트북에만 있던 것

- Claude 메모리(~/.claude/projects/...): 핵심 선호는 CLAUDE_HANDOFF_KO.md에 옮겨 적음 (명령은 코드블록 하나당 하나, 원리 설명 위주).
- Desk 계정 비밀번호: 문서에 저장하지 않음.

## 9. 두 컴퓨터를 오가며 작업하기 (2~7단계를 한 번 마친 뒤)

작업 시작 전, 다른 컴퓨터에서 올린 내용 받기:

```bash
git pull
```

작업 후 바뀐 파일 확인:

```bash
git status
```

올릴 파일 담기:

```bash
git add -A
```

변경 내용 설명과 함께 기록:

```bash
git commit -m "변경 내용 한 줄 설명"
```

GitHub에 올리기 (Username: 아이디, Password: 토큰):

```bash
git push
```

pull로 fr3_skills 등 src/ 아래 코드가 바뀌었으면 다시 빌드한다 (symlink-install이라 Python 파일만 바뀐 경우는 대개 불필요, 새 파일/패키지가 생기면 필요):

```bash
colcon build --symlink-install --packages-select fr3_skills
```

주의: franka_ros2 안을 고쳤다면 저장소에는 패치 파일만 올라가므로 패치를 다시 만들어야 한다. 이 경우 Claude에게 요청한다.
