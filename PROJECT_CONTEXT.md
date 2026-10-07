# Franka 프로젝트 현장 정보 및 재개 기록

## 최신 인수인계: 2026-10-02 — Claude로 이전

이 절이 아래 과거 기록보다 우선한다. 전체 인수인계는 [CLAUDE_HANDOFF_KO.md](CLAUDE_HANDOFF_KO.md)를 먼저 읽는다.

- 사용자가 RViz에서 Plan/Execute를 눌렀지만 실물은 움직이지 않았다고 보고했다. 실물 모션 성공은 아직 없다.
- 오늘 파일 재확인: move_group.launch.py의 allow_trajectory_execution=False 유지. 기본 bringup은 상태 broadcaster만 활성화하는 구성이다. 실행 가능한 trajectory 연결은 아직 구현하지 않았다.
- 오늘 ROS 조회에서 /controller_manager 서비스가 응답하지 않았고 /move_group은 Node not found였다. 당시 조회 결과일 뿐 현재 로봇 상태를 단정하지 않는다.
- 이후 RViz와 RViz 단독 실행 모두 Failed to create an OpenGL context / BadValue / Unable to create a suitable GLXContext 발생. LIBGL_ALWAYS_SOFTWARE=1을 붙인 실행도 사용자 보고상 실패했다.
- 실제 launch.log에는 move_group 초기화 완료 후 Ctrl+C(SIGINT)가 기록되고 이어 exit -11이 발생한다. 종료 중 충돌 가능성이 있으나 원인은 미확정이다. RViz 그래픽 오류와 동일 원인이라고 단정하지 않는다.
- 사용자가 Ctrl+Z로 launch 또는 rviz2를 일시정지한 기록이 있다. jobs로 확인하고 해당 작업을 fg 후 Ctrl+C로 정리하도록 안내했다. 실제 정리 완료 여부 미확인.
- glxinfo -B 결과는 아직 받지 못했다. 도구 환경 DISPLAY=:0, XDG_SESSION_TYPE=x11 확인; 사용자 터미널 전체 그래픽 환경을 대변하지 않는다.
- 사용자가 노트북 재부팅을 제안했고, 파일 저장 → ROS 프로그램 정상 종료 → 노트북 재시작 → bringup 전 rviz2 단독 확인을 안내했다. 재부팅 수행 및 복구 결과 미확인. 커널/드라이버/패키지 변경 없음.
- 실물 사진: Franka Hand 장착. 테이블 600×600×800mm, 3030 프로파일, 상판 없음(추후 설치 예정). 베이스는 한 변 중앙 부근에 직접 볼트/너트/스프링 와셔로 고정, 별도 플레이트 없다는 사용자 설명. 정확한 기준좌표/오프셋/강성 검증 없음.
- 사용자는 작은 실물 동작 준비·시험을 원하며 승인 질문 반복을 원하지 않는다. 기존 승인 범위에서 실행 구성 준비는 진행하되 실제 움직임 전에 명령·변위·상태를 확인한다. TCP z>=0만으로 팔 전체와 프로파일 충돌을 배제할 수 없다.
- Codex/VS Code 응답 멈춤도 보고됐다. 확장 재설치 후에도 반복. VS Code 버전/확장 로그 미확보, rtprio 또는 버전이 원인이라는 증거 없음.
- 오늘 문서 인수인계만 수정한다. 로봇 이동, 실행 controller 활성화, Git commit/push, 재설치는 수행하지 않는다.

## 이전 진행: 2026-10-01

아래 기록이 9월 28일의 과거 상태보다 우선한다.

- 사용자 보고: FCI 활성화 및 관절 잠금 해제 완료.
- 사용자가 `/etc/security/limits.d/99-franka-research.conf`에 계정별 soft/hard rtprio 99를 설정하고 재로그인함. `ulimit -r=99` 및 bringup의 FIFO priority 98 성공 로그 확인. 커널 변경 없음.
- 기본 bringup 실물 연결 성공. joint_state_broadcaster 및 franka_robot_state_broadcaster active, 7개 실물 관절 측정값 수신 확인.
- 상세 상태 broadcaster의 잠금 실패가 반복됨. 상태 수신은 약 1kHz였음.
- 최소 진단 변경: franka_bringup/config/controllers.yaml에서 상세 상태 broadcaster에만 update_rate 100 추가. 하드웨어/controller manager 1000Hz 유지, 오류 로그와 ERROR 반환 설정 유지.
- 변경 후 사용자 측정: 상세 상태 약 99.97~100.02Hz, 간격 9~11ms. 제공한 후속 로그에 잠금 오류 없음. 제한된 시험의 개선이며 장시간 안정성 또는 모션 검증 완료는 아님.
- MoveIt 준비: 기존 move_group.launch.py의 인자 선언, OMPL 구성, kinematics 파라미터 계층, 실제 관절 토픽 remap 보완. allow_trajectory_execution=False로 고정. controller manager/그리퍼/동작 컨트롤러를 실행하지 않음.
- RViz의 그룹명 fr3_manipulator를 실제 fr3_arm으로 수정하고 MotionPlanning 표시 활성화.
- Python 문법, launch 인자 목록, Xacro 생성 및 SRDF 그룹 검증 완료. 이후 사용자 실행으로 RViz 표시, fr3_arm MoveGroup 연결 및 OMPL/RRTConnect 경로 계획 성공 확인. 로그: Motion plan was computed successfully, 계획 시간 0.0138672초. 실제 궤적 실행은 하지 않음.
- 첫 MoveIt 검증은 load_gripper=false인 팔 모델로 진행. 물리 그리퍼와 테이블의 충돌 모델이 빠져 있으므로 실제 동작 근거로 사용하지 않는다. 실행 기능은 비활성화됨.
- 다음: 현재 실물 관절값과 MoveIt 시작 상태 일치 확인, 실제 Franka Hand와 테이블 등 장애물의 모델·좌표 확인 후 충돌 모델 준비. 그 이후 작은 경로를 계획하고 검토한 뒤 실행 연결을 별도 검증한다. 기존 통합 moveit.launch.py를 기본 bringup과 동시에 실행하지 않는다.

최종 업데이트: 2026-10-01. 사용자가 Codex 확장을 재설치하기 위해 진행 기록 저장을 요청함.
전체 목표와 초기 조사: [FRANKA_PROJECT_PLAN_KO.md](FRANKA_PROJECT_PLAN_KO.md)

## 과거 참고: 2026-09-28 중단 당시 상태 (위 최신 기록이 우선)

- Desk 접속 및 사용자 admin 로그인 확인 완료.
- 사용자 제공 Dashboard 화면: Control 시스템 버전 **5.8.1**, Control Status **ok**, Safety **ok**, Arm **Arm3R / connected**.
- 마지막 Desk 화면: **Joints locked**, **NOT TRIGGERED**, **NOT ENABLED**, End Effector **Powered Off**, Safety Scenario **Work**.
- System 화면: Franka Control Interface (FCI) **1.0.0 설치됨**. 이 숫자는 Control 시스템 버전이 아니다.
- 사용자가 시스템 메뉴에 **Activate FCI** 항목이 있다고 확인함.
- **FCI 활성화는 아직 지시하거나 실행하지 않았으며, 사용자의 실행 보고도 없음.** 마지막 안내는 누르지 말고 먼저 실행 중인 제어 프로그램을 확인하자는 것이었음.
- ROS2/Franka 실행 프로세스 확인은 아직 하지 못함. 다음 첫 작업임.
- ROS launch, 관절 잠금 해제, 모션 명령, 그리퍼 명령은 이 세션에서 실행하지 않음.
- 위 상태는 저장 시점 직전 사용자 화면에 근거한 기록이다. 노트북/로봇 재시작 후 반드시 다시 확인한다.

## 네트워크: 최종 설정

| 대상 | 포트/인터페이스 | 주소 |
|---|---|---|
| 노트북 유선 | enp129s0 | 172.16.0.10/24 |
| Control Box | C2 — Shop Floor network | 172.16.0.2/24 |
| 로봇 베이스 | X5 — Robot network | 192.168.0.1/24 |

사용자가 노트북 LAN을 Control Box에 직결했다고 확인함. Dashboard에서 C2/X5 주소 구분을 확인함.
FCI는 C2 연결을 사용한다. 현재 Control Box 연결을 유지하며 X5로 옮기지 않는다.
Desk 주소: **https://172.16.0.2/desk/**

NetworkManager 프로필:

- 이름: **franka-direct**
- 기존 Wired connection 1 프로필은 보존.
- ipv4.method=manual, ipv4.addresses=172.16.0.10/24
- IPv4 게이트웨이/DNS 미지정, ipv4.never-default=yes
- ipv4.dad-timeout=3000, ipv6.method=disabled
- **connection.autoconnect=yes, connection.autoconnect-priority=100**
- 처음에는 자동 연결을 껐으나, 반복 접속 문제 후 위 설정으로 수정하고 조회로 검증함.
- 변경 당시 Wi-Fi 기본 경로 유지 확인. 인터넷 서비스 자체는 시험하지 않음.
- 실제 노트북 재부팅 후 자동 연결 여부는 아직 시험하지 않음.
- 유선 포트를 다른 네트워크에 사용할 때는 그 용도에 맞는 프로필로 전환해야 함.

재개 시 조회용 명령 (로봇 모션 없음):

```bash
nmcli -f GENERAL.STATE,GENERAL.CONNECTION,WIRED-PROPERTIES.CARRIER,IP4.ADDRESS device show enp129s0
ip route get 172.16.0.2
ping -n -c 3 -W 2 172.16.0.2
```

링크가 정상인데 프로필이 비활성인 경우 기존 설정을 다시 켜는 명령:

```bash
nmcli connection up franka-direct
```

carrier가 off이면 프로필 활성화만으로 해결된다고 단정하지 않는다. 로봇 부팅 상태와 물리적 링크부터 확인한다.

## 접속 및 재부팅 문제 이력

1. 최초 유선 DHCP 설정에서 IPv4를 받지 못해 로봇 대상 트래픽이 Wi-Fi로 나감.
2. franka-direct 고정 IP 프로필 생성 후 ping 3/3 성공, 이후 HTTPS /desk/ 응답 200 OK 확인.
3. 기존 DHCP 프로필이 선택되거나 유선 프로필이 비활성화되는 문제가 반복돼 자동 연결 ON, 우선순위 100으로 수정.
4. 사용자 Desk 화면에 Non-recoverable safety error가 표시됨. 원인 상세 코드와 로그는 확보하지 못함.
5. 사용자가 Desk Reboot를 수행했다고 보고. 약 10분 이상 흰색 점멸과 웹 접속 실패를 보고함. 이때 노트북 유선 carrier off를 도구로 확인.
6. 사용자가 Control Box 전원을 껐다 켠 뒤 Desk가 복구되었다고 보고함. 이 물리 조작은 사용자가 수행했으며 에이전트가 원격 실행한 것이 아님.
7. 이후 화면에서 Joints locked 및 Dashboard의 Status/Safety ok 확인.

재부팅 정체와 안전 오류의 근본 원인은 미확인이다. 전원 재투입을 일반 해결책으로 간주하지 않는다. 같은 현상이 재발하면 상세 오류와 로그를 확보하고 해당 장비 매뉴얼 및 지원 절차를 따른다.
브라우저를 닫는 것은 로봇 정상 종료 절차가 아니다.

## 기존 소프트웨어와 호환성

- Ubuntu 22.04.5, ROS2 Humble
- 기존 커널 6.8.0-138-generic (변경 없음)
- libfranka 0.15.0
- franka_ros2 2.0.2
- franka_description 1.0.1
- Control 5.8.1은 기존 libfranka/franka_ros2 조합의 공식 호환 범위에 해당.
- 재설치·업데이트·커널 변경하지 않음. FCI를 통한 실물 상태 수신은 이후 확인했으나 실제 모션 제어 성능은 미검증.
- 기존 예제 YAML의 robot_ip=172.16.0.3은 실제 C2 주소와 다름. 아직 소스 수정하지 않았음. 향후 실제 launch 파일 인자를 검토해 172.16.0.2를 명시한다.
- 기존 사용자 수정: franka_semantic_components/CMakeLists.txt에 controller_interface 의존성 추가. 보존함.
- libfranka communication_test 예제에는 모션이 포함됨. 통신 확인용으로 실행하지 않는다.

공식 근거:

- [Franka 호환표](https://franka.de/fr3-compatibility-matrix)
- [FR3 매뉴얼: C2 FCI 연결 설명 포함](https://download.franka.de/documents/Product%20Manual%20Franka%20Research%203_R02210_1.1_DE.pdf)
- [FR3 매뉴얼: 상태 표시 및 종료 절차](https://www.franka.de/hubfs/Product%20Manual%20Franka%20Research%203_R02210_1.5_EN-1.pdf?hsLang=en)

## 계정

일반 계정명 admin, Safety 계정명 safety는 사용자 제공 정보다. admin 로그인은 화면에서 확인함. 비밀번호는 이 문서에 기록하지 않았다. Safety 계정 사용이나 안전 설정 변경은 수행하지 않았다.

## 다음 세션 진행 순서

1. 이 문서의 최신 기록과 FRANKA_PROJECT_PLAN_KO.md를 읽는다. 성공한 조사·상태 측정을 불필요하게 반복하지 않는다.
2. 실행 중인 노드·터미널을 확인하고 중복 bringup을 피한다. 확장 재설치 또는 VS Code 종료가 ROS 프로세스/로봇 종료를 보장하지 않는다.
3. Desk의 현재 오류 상태, FCI 활성 상태, 관절 상태를 다시 확인한다. 과거 화면을 현재 상태로 가정하지 않는다.
4. 필요하면 아래 검증된 두 launch를 실행한다. 이 구성에는 팔 모션용 trajectory 컨트롤러가 없다.
5. 실물 관절값과 MoveIt 시작 상태 일치를 확인한다. RViz 목표 자세 표시와 현재 상태 표시를 구분한다.
6. 실제 장착 Franka Hand와 테이블/프로파일 등 장애물의 치수·좌표 및 TF를 확인한다. 현재 팔 전용 모델로 실물 실행하지 않는다.
7. 충돌 모델과 작은 경로를 검토한 후에만 실행 가능한 trajectory 컨트롤러 및 MoveIt 실행 구성을 준비한다. 움직이기 전 명령과 움직임을 설명하고 상태를 확인한다.
8. 작은 동작 → HOME/READY 등의 검증된 자세 → 그리퍼 → 재사용 함수/클래스 → Bin Picking 순서로 진행한다. HOME/READY 좌표는 아직 정의되지 않았다.

### 검증한 실행 구성

터미널 1: 실물 하드웨어와 상태 broadcaster (이미 켜져 있으면 중복 실행 금지)

```bash
source /opt/ros/humble/setup.bash
source ~/franka_ros2_ws/install/setup.bash
ros2 launch franka_bringup franka.launch.py robot_ip:=172.16.0.2 arm_id:=fr3 use_fake_hardware:=false load_gripper:=false
```

터미널 2: MoveIt 및 RViz, 계획 전용

```bash
source /opt/ros/humble/setup.bash
source ~/franka_ros2_ws/install/setup.bash
ros2 launch franka_fr3_moveit_config move_group.launch.py robot_ip:=172.16.0.2 load_gripper:=false
```

move_group.launch.py는 allow_trajectory_execution=False로 고정되어 있다. 실제 하드웨어 노드/컨트롤러/그리퍼를 추가 실행하지 않는다. 설치된 launch/config는 소스에 대한 심볼릭 링크이므로 이번 설정 변경에 재빌드가 필요하지 않았다.

RViz에서 MotionPlanning 패널이 숨겨지면 Panels 메뉴에서 표시한다. 모델 로딩과 Ready to take commands for planning group fr3_arm 및 계획 성공 로그를 사용자 실행으로 확인했다. /recognize_objects 서버 없음은 현재 인식 기능을 실행하지 않는 구성에서 나타났고, 팔 계획 성공을 막지 않았다. QVariant 경고의 구체적 원인은 미확인이다.

### 변경 파일 및 복원 단위

- src/franka_ros2/franka_bringup/config/controllers.yaml: 상태 broadcaster의 update_rate: 100 한 줄 추가. 하드웨어 루프 1000Hz 및 오류 보고 유지. 복원 시 이 추가 줄만 제거하면 기존 주기로 돌아간다.
- src/franka_ros2/franka_fr3_moveit_config/launch/move_group.launch.py: 빠진 인자 선언, OMPL 계획 구성, robot_description_kinematics 계층, 관절 토픽 remap, 계획 전용 제한, RViz 실행 추가. 기존 YAML의 panda 그룹 이름은 이 launch에서만 fr3_arm으로 변환한다.
- src/franka_ros2/franka_fr3_moveit_config/rviz/moveit.rviz: Planning Group을 fr3_arm으로 수정, MotionPlanning 표시 활성화.
- 기존 franka_semantic_components/CMakeLists.txt의 controller_interface 추가는 사용자 기존 변경으로 보존한다.
- /etc/security/limits.d/99-franka-research.conf: 사용자가 직접 계정의 soft/hard rtprio 99 설정. 재로그인 후 적용 및 FIFO priority 98 성공 확인.

Git reset이나 패키지 교체로 변경을 일괄 삭제하지 않는다. Git 커밋/푸시는 하지 않았다.

### 남은 미확인 사항

- 상태 발행 잠금 오류: 100Hz 변경 후 제공한 짧은 측정/로그에서 재발 없음. 장시간 시험과 제어 부하 아래 검증은 미완료. 근본 원인을 완전히 확정한 것으로 기록하지 않는다.
- 실제 궤적 실행/팔 모션/그리퍼 모션은 아직 미검증.
- 기존 통합 MoveIt launch의 그리퍼 액션 이름 fr3_gripper와 실제 노드 franka_gripper 불일치 가능성은 미해결. 이번 계획 전용 구성은 그리퍼를 사용하지 않는다.
- 실물 그리퍼/테이블 충돌 모델, 목표 pose의 프레임과 TCP, HOME/READY 좌표는 미정.
- 재부팅 정체 및 이전 안전 오류 원인은 미확인.
- System의 FACTORY RESET 또는 MOVE TO PACK POSE를 시작 자세 복귀 목적으로 사용하지 않는다.

## 작업 원칙 및 종료 시점

- 분석 → 설명 → 실행 → 검증. 실물 모션 전 무엇이 움직이는지와 명령을 먼저 보여주고 상태·작업 공간을 확인한다.
- 커널/드라이버/ROS2/Franka 버전 변경, 워크스페이스 재생성 금지. 수정은 최소화.
- 인식·학습·카메라 보정·Bin Picking 구현은 아직 시작하지 않는다.
- 이번 중단 요청은 Claude로 작업을 넘기기 위한 기록 저장이다. 로컬 문서만 저장하며 Git 커밋/푸시, GitHub 업로드는 하지 않는다.
- 에이전트는 로봇 정상 종료를 수행하지 않았다. 노트북 종료가 로봇 종료를 의미하지 않는다.
