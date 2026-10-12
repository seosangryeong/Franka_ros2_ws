# Claude 인수인계 — Franka 실물 제어

최종 기록: 2026-10-12 (한국 시간). 이 문서를 먼저 읽고 PROJECT_CONTEXT.md 및 FRANKA_PROJECT_PLAN_KO.md를 참고한다. 과거 기록과 충돌하면 최신 날짜의 확인된 결과를 우선한다. 저장 시점의 실시간 로봇 상태는 조회하지 않았다.

**Git 커밋이 밀려있다.** 10/7 이후 작업이 전부 로컬에만 있고 커밋/푸시 안 됨(아래 "2026-10-12" 절 참고). 다른 컴퓨터에서 이어서 작업하면 이 내용이 없다 — 먼저 `git status`로 확인할 것.

**2026-10-07부터 작업 환경이 바뀌었다.** 아래 과거 기록(2026-10-02 이전)의 워크스페이스 경로 `/home/research_108_01/franka_ros2_ws`, 계정 `research_108_01`, 이더넷 `enp129s0`는 **옛 노트북(HP OMEN) 기준**이다. 현재는 **새 노트북(hostname wynz-NUC11PHi7, 계정 wynz, 워크스페이스 `~/franka_ros2_ws` = `/home/wynz/franka_ros2_ws`, 이더넷 `enp89s0`)**로 GitHub 저장소를 통해 이전했다. 자세한 내용은 맨 아래 "2026-10-07 오후 (새 노트북 NUC11PHi7)", "2026-10-07 저녁 — move_to_pose + pose_listener", "2026-10-08 — 그리퍼 실물 검증 + RViz 연동 + 제어 통합", "2026-10-08 오후~저녁 — pick/place, 실물 충돌 사고·복구, 테이블 모델 정밀 보정" 절 참고.

**실물 충돌 사고가 있었다(2026-10-08).** 지금 실물 작업을 재개하기 전에 맨 아래 "2. 실물 충돌 사고와 복구" 절을 반드시 먼저 읽는다. 외부 인에이블링 장치(펜던트) 없이는 Desk 공식 복구 절차를 못 쓴다는 것도 확인한다.

## 사용자 목표와 작업 방식

Ubuntu 22.04 / ROS2 Humble / VS Code / 실물 Franka Research 3. 워크스페이스는 /home/research_108_01/franka_ros2_ws. 인수인계 없이 시작한 사용자라 설명은 한국어로 쉽고 짧게 한다. 사용자는 Piper처럼 목표 pose → MoveIt IK/경로계획 → 실제 이동을 원한다.

최종 구조: 사용자 코드 → MoveIt2 → ros2_control의 trajectory controller → franka_ros2 하드웨어 → libfranka/FCI → 실물. Desk는 준비·상태·FCI 활성화에 사용하며 Desk 자체에서도 작업 작성이 가능하다. launch에 따라 하드웨어와 MoveIt이 통합 실행될 수 있으므로 반드시 세 터미널로 고정할 필요는 없다.

우선순위: 환경/통신/상태 → MoveIt 실물 연결 → 현재 자세 근처 작은 이동 → HOME/READY/Pose A/B → 그리퍼 → 재사용 API → Bin Picking → OBSBOT RGB 카메라/좌표변환. 카메라와 인식 구현은 아직 시작하지 않는다.

향후 API 희망: move_to_pose(x,y,z,qx,qy,qz,qw), open_gripper(), close_gripper(), move_home(), move_ready(), pick(object_pose), place(place_pose). 아직 구현하지 않았고 HOME/READY도 정의되지 않았다. RGB의 픽셀만으로 깊이는 정해지지 않아 향후 평면/높이/형상 조건과 보정이 필요하다. 처음부터 반드시 직접 학습해야 하는 것은 아니다.

## 가장 중요한 현재 상태

1. 기존 소프트웨어 조사 완료, Desk 및 FCI를 통한 실물 상태 수신 성공.
2. rtprio 적용 및 FIFO priority 98 성공. broadcaster 100Hz로 줄인 짧은 시험에서 잠금 오류 재발 없음. 장시간 안정성은 미검증.
3. RViz 및 MoveGroup fr3_arm 연결, OMPL RRTConnect Plan 성공(0.0138672초).
4. 사용자가 Execute를 눌렀지만 실물은 움직이지 않았다고 보고. **실물 이동 성공은 없다.** 계획 전용 launch에 allow_trajectory_execution=False가 남아 있고 실행 controller 연결도 준비되지 않았다. True 한 줄만 바꿔 완료된다고 처리하지 않는다.
5. 그 후 RViz GLX/OpenGL 오류로 화면도 안 열림. RViz 단독 및 소프트웨어 렌더링도 실패. **지금은 그래픽 복구가 첫 진단 과제다.**
6. 노트북 재부팅을 안내했지만 수행/복구 확인은 아직 없다. 실제 로봇·ROS 현재 상태는 새로 확인해야 한다.

## 기존 환경 및 네트워크

- Ubuntu 22.04.5, 기존 커널 6.8.0-138-generic. 변경 없음.
- franka_ros2 2.0.2, libfranka 0.15.0, franka_description 1.0.1.
- Control 시스템 5.8.1, Arm3R connected 및 Status/Safety ok 화면 확인 이력. FCI feature 1.0.0은 시스템 버전과 별개. 공식 호환표는 PROJECT_CONTEXT.md 참고.
- src/franka_ros2, src/libfranka, src/franka_description, src/olvx_descriptions_module(olv_module_descriptions 0.0.1). 전체 15개 패키지, build/install/log 존재, 마지막 조사 빌드 2026-09-11 15:39 성공. MoveIt2 및 joint_trajectory_controller 설치 확인.
- 노트북 enp129s0: 172.16.0.10/24.
- Control Box C2 Shop Floor: 172.16.0.2/24. Desk https://172.16.0.2/desk/ 및 FCI 연결 대상.
- 베이스 X5 Robot network: 192.168.0.1/24. 현재 노트북 C2 직결 유지.
- NetworkManager franka-direct: manual IPv4, gateway/DNS 없음, never-default yes, autoconnect yes priority100, IPv6 disabled, dad-timeout3000. 기존 Wired connection1 보존. Wi-Fi 기본 경로 보존.
- admin 및 safety 계정 존재. 비밀번호는 문서에 저장하지 않음.
- 과거 Non-recoverable safety error와 Desk reboot 후 흰색 점멸/접속 불능 기록. 사용자가 Control Box 전원 재투입 후 복구. 원인 미확정, 일반 재부팅 방법으로 권장하지 않는다. Factory Reset/Pack Pose 실행 안 함.

## 변경 파일: 오늘 재확인한 Git 상태

src/franka_ros2에서 수정된 네 파일:

| 파일 | 변경 및 의미 |
|---|---|
| franka_bringup/config/controllers.yaml | 상세 상태 broadcaster update_rate:100 추가. manager1000 유지, lock_try_count5/sleep5, lock_log_error:true, lock_update_success:false 유지. 오류 숨김 아님. |
| franka_fr3_moveit_config/launch/move_group.launch.py | 인자 선언, kinematics 계층, OMPL 구성, panda_arm→fr3_arm 매핑, joint_states→franka/joint_states remap, RViz 옵션. allow_trajectory_execution=False. 자체 hardware/controller/gripper launch 없음. |
| franka_fr3_moveit_config/rviz/moveit.rviz | Planning Group fr3_arm, MotionPlanning 활성화. |
| franka_semantic_components/CMakeLists.txt | 사용자의 기존 controller_interface 의존성 변경. 보존할 것. |

설치 launch/config는 소스 symlink여서 위 수정 당시 재빌드 불필요. Python 문법/show-args/Xacro/SRDF 그룹 검증 완료 이력. Git reset/패키지 교체로 일괄 되돌리지 말 것. commit/push 안 함.

시스템 파일 /etc/security/limits.d/99-franka-research.conf는 사용자가 직접 작성:

```text
research_108_01 soft rtprio 99
research_108_01 hard rtprio 99
```

재로그인 후 ulimit -r99, controller_manager FIFO98 성공. 99는 허용 상한이며 그 자체가 CPU를 사용하는 설정은 아니다.

**기존 별도 파일 주의:** franka_fr3_moveit_config/config/fr3_ros_controllers.yaml에는 원래 lock_log_error:false / lock_update_success:true가 있다. 이번 기본 bringup 진단에서 사용하는 controllers.yaml과 다르다. 통합 launch로 전환하면서 오류가 안 보이는 것만으로 해결 판정하면 안 된다.

## 검증한 launch와 실행 연결의 빈 부분

각 터미널에서 먼저:

```bash
cd ~/franka_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

터미널1 — 실물 상태 bringup (중복 실행 금지):

```bash
ros2 launch franka_bringup franka.launch.py robot_ip:=172.16.0.2 arm_id:=fr3 use_fake_hardware:=false load_gripper:=false
```

joint_state_broadcaster 및 franka_robot_state_broadcaster active 확인. 팔 동작용 fr3_arm_controller는 이 구성으로 활성화하지 않았다.

터미널2 — 계획 전용 MoveIt/RViz:

```bash
ros2 launch franka_fr3_moveit_config move_group.launch.py robot_ip:=172.16.0.2 load_gripper:=false
```

RViz 없는 분리 진단 인자 use_rviz:=false 지원. 실행 안내는 했지만 해당 방식 정상 유지 결과는 아직 없다.

기존 moveit.launch.py는 하드웨어/controller manager까지 포함하는 통합 구성이다. **기본 bringup과 동시에 켜지 말 것.** 기존 fr3_ros_controllers.yaml의 fr3_arm_controller는 effort JointTrajectoryController, position/velocity 상태, joint1~7 및 PID gains 정의. 이를 현재 manager에 정확히 어떻게 로드/연결할지 아직 구현하지 않았다. MoveIt controller mapping(fr3_controllers.yaml), 실제 FollowJointTrajectory 서버, 관리 namespace와 인터페이스를 함께 검증해야 한다.

기존 gripper 참조 fr3_gripper와 실제 노드 franka_gripper 불일치 가능성 미해결. load_gripper=false로 계획했고 실물 Hand가 모델에 빠져 있다. 그리퍼 homing/open/close 모두 미시험.

## 상태 발행 잠금 오류 경과

원래 로그: Failed to lock the realtime publisher after 5 attempts; controller update ERROR 반복. 약1kHz 관절/상태 수신은 되기도 했고 한번 topic hz에서 미발행 경고도 있었다. topic 존재만으로 정상 발행을 판단하지 않는다.

broadcaster 소스 trylock 재시도/실패시 해당 갱신 누락 동작 조사. 설치된 ros2_control의 개별 controller update_rate 지원 확인 후 상세 broadcaster에만100Hz 설정. 사용자 param100 및 약99.97~100.02Hz, 9~11ms 간격 확인. 후속 제공 로그에 lock ERROR 없음. 제어 루프1000Hz 변경 안 함. 근본 원인 확정/장시간 실기 안정성 인증은 아니다. CLI message lost 한 건을 FCI 패킷 손실로 단정하지 않는다.

실물 /franka/joint_states 이름 순서가 joint1,3,6,7,2,4,5였음. **항상 name으로 position 매핑**한다. 과거 측정 joint1~7 rad:
[-0.195533899, 0.088273913, 0.114479593, -2.235051960, 0.072861632, 2.281744737, 0.753980274]. 오래된 참고값이며 현재 목표/HOME으로 사용하지 말 것.

## 오늘 그래픽/종료 오류와 증거

RViz: Failed to create an OpenGL context. BadValue / Unable to create a suitable GLXContext, OgreGLXContext.cpp line60. 저장된 MoveIt RViz 설정 없이 rviz2 단독도 같은 오류.

사용자가 아래 실행도 실패했다고 보고:

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch franka_fr3_moveit_config move_group.launch.py robot_ip:=172.16.0.2 load_gripper:=false
```

로그 경로:
- ~/.ros/log/2026-10-02-14-35-08-334959-2204-193370/launch.log
- ~/.ros/log/move_group_193396_1790919308544.log
- ~/.codex/attachments/5b0f815b-00de-42e5-b69c-be526eaf412e/Pasted text.txt

launch.log에서 move_group 초기화 완료 → Ctrl+C(SIGINT) → exit -11 순서가 확인됐다. 종료 중 충돌 가능성이 있으며 시작부터 실패했다고 단정하지 않는다. RViz 종료시 SIGTERM10초 후 SIGKILL / exit-9 기록도 있다. 종료되지 않아 강제 정리된 기록이며 새로운 원인 증거는 아니다.

move_group 로그에는 No controller_names specified / Returned 0 controllers도 있다. 실행 연결 누락의 추가 근거. /recognize_objects 없음 및 Octomap sensor plugin 없음은 인식 미구성 상태에서 관측됐고 과거 Plan 성공을 막지 않았다.

사용자가 Ctrl+Z를 여러 번 사용: 이는 종료가 아니라 Stopped 상태다. 같은 터미널 jobs -l 확인 → 해당 번호 fg %N → Ctrl+C 안내. 무조건 특정 job 번호를 재사용하지 말 것. 수행 완료 미확인.

도구 환경 DISPLAY=:0, SESSION=x11. sandbox ps에 ROS 프로세스 없음은 호스트 상태를 보장하지 않는다. sandbox ROS socket PermissionError는 도구 권한 제한이며 사용자 로봇 고장 아님. 권한 확대 조회에서는 그 시점 controller_manager 응답 없음 / move_group Node not found.

glxinfo -B 및 사용자 그래픽 변수 조회를 요청했지만 출력 못 받음. glxinfo 도구도 설치 여부 미확정, 진단 위해 무조건 설치하지 않는다. 소프트웨어 렌더링 실패만으로 GPU 고장을 단정하지 말 것.

사용자 노트북 재부팅 의향: 저장 → MoveIt/RViz와 bringup Ctrl+C 종료 → 정지 확인 → 노트북 정상 재시작 → ROS bringup 전에 source /opt/ros/humble/setup.bash 및 rviz2 단독 시험 안내. 완료/결과 미확인. 이 그래픽 문제 때문에 Control Box 전원 재투입은 제안하지 않았다.

## 현장 사진과 안전 범위

테이블600×600×800mm, 3030 프로파일, 상판 없음(추후 설치). 베이스는 한 변 중앙 부근에 직접 볼트/너트/스프링 와셔로 고정, 별도 플레이트 없음(사용자 설명). 내부/외곽 레일, 아래 상자, 케이블, 주변 가구가 사진에 보인다. 실제 Hand 장착. 사진에서 정확한 TF/오프셋/고정 강성은 알 수 없다.

사용자는 상세 CAD보다 작은 실물 제어 진행을 원하고, 아래 프로파일 접촉만 피하면 된다고 설명했다. 실행 구성 준비와 작은 실물 시험 진행 의사는 반복 확인됐다. 같은 승인 질문을 반복하지 말고 가능한 준비를 진행한다. 다만 TCP z>=0 제한은 팔 전체 충돌 회피가 아니다. 비상정지가 충돌 방지를 보장한다고 설명하지 않는다. 예제 Cartesian controller가 자동으로 큰 궤적을 만드는지 확인 없이 실행하지 않는다.

첫 시험 후보로0.01rad 단일 관절 변경을 언급했으나 관절/방향/속도/목표는 미선정. **실제 명령으로 확정된 숫자가 아니다.** 현재 상태와 전체 경로 및 환경을 확인해 결정한다.

## Claude가 다음에 할 순서

1. 재부팅 여부, 남은 일시정지 프로세스 및 RViz 단독 결과 확인. glxinfo가 있으면 glxinfo -B, DISPLAY/session 및 관련 렌더링 환경변수 조회. 원인 없이 드라이버/커널 변경 금지.
2. 현재 Desk FCI/관절/오류 및 실제 ROS node/controller/joint state 확인. 중복 hardware launch 금지. 이전 성공값을 현재로 간주하지 않는다.
3. 기존 파일을 활용해 실제 trajectory controller + MoveIt mapping/action 연결을 구체적으로 준비. 아직 실행을 허용하지 않은 구성임을 사용자에게 명확히 설명. 현재 경로를 그대로 무작정 실행하지 않는다.
4. 실물 Hand/프로파일 충돌 범위를 반영하고 현재 관절과 계획 시작 상태 일치 확인. 필요한 최소 정보로 진행하며 완전한 CAD를 필수로 고집하지 않는다.
5. 무엇이 얼마나 움직이는지/명령을 먼저 보여주고 현재 근처 작은 계획 검토 → 실행 → 실제 상태/오류 검증.
6. 그 후 검증된 HOME/READY, 그리퍼, API, Bin Picking 순으로 확장.

## 환경 보존 및 인수인계 주의

커널 설치/변경 금지. 네트워크 드라이버/ROS/libfranka/franka_ros2 버전 변경과 패키지 재설치는 필요 근거 없이 하지 않는다. 기존 workspace 삭제·재생성 금지. 작은 수정만 한다. 물리 이동 전 설명/명령/상태 확인 원칙 유지. 사용자 질문에는 짧게 먼저 답하고 도구 작업 중 진행 상황을 알린다.

Codex 응답이2~3회 질문 뒤 멈추고 재접속하면 복구된다는 사용자 보고, 확장 재설치 후에도 반복. VS Code 버전/로그 미확보. rtprio99나 오래된 VS Code가 원인이라고 확정하지 않았다. VS Code/확장 삭제나 시스템 업데이트 수행 안 함.

이번 인수인계에서는 문서만 저장. 새 제어 패키지/모션 스크립트 생성, controller 활성화, 로봇·그리퍼 이동, Git commit/push 수행 안 함. 로봇 정상 종료도 에이전트가 수행하지 않았다.

## 2026-10-02 15:20 추가 (Claude)

- 노트북 재부팅 확인(부팅 15:07). 남은 ROS/일시정지 프로세스 없음. 172.16.0.2 ping 정상.
- GPU: RTX 5090 Laptop, NVIDIA 580.178.04, prime on-demand. **rviz2 단독 정상(OpenGL 4.6, GLX 오류 없음)** → 그래픽 문제는 재부팅으로 해소. 드라이버 변경 없음. glxinfo 미설치(설치 안 함).
- 실행 연결 준비(실물 미실행):
  - 새 파일 franka_fr3_moveit_config/config/fr3_arm_controller_real.yaml: effort JTC, 기존 PID 게인 동일, constraints(trajectory 0.05rad, goal 0.01rad, goal_time 0.5s) 추가. controllers.yaml은 변경 안 함.
  - move_group.launch.py에 `execute` 인자 추가(기본 false → 기존 계획 전용 동작 유지). true일 때 fr3_arm_controller 매핑(그리퍼 제외), moveit_manage_controllers=false, allowed_start_tolerance 0.01.
  - franka_fr3_moveit_config만 symlink 재빌드.
- fake hardware(ROS_DOMAIN_ID=77, localhost)로 검증: spawner -p ... --inactive 로드 OK, MoveIt "Added FollowJointTrajectory controller", /fr3_arm_controller/follow_joint_trajectory 확인, activate/deactivate 전환 OK. 궤적 실행은 fake에서도 안 함. 테스트 프로세스 정리 완료.
- 실물 이동 성공 여전히 없음. 실물에서 effort JTC 활성화 시 동작은 미검증.

## 2026-10-02 오후 실물 결과 (위 "실물 이동 성공 없음"을 대체)

- spawner `--inactive -p fr3_arm_controller_real.yaml` → activate → RViz Plan/Execute로 **실물 이동 성공**(여러 번 `Goal reached, success!`). 관절2 약0.21rad 등.
- **미해결: ros2_control_node exit -6(abort) 2회**(15:40:28, 15:51:09). 둘 다 Execute 성공 후 fr3_arm_controller를 active로 둔 채 대기 중(44초/86초 후). 원인 메시지는 터미널1 화면에만 출력되어 미확보. 후보: libfranka communication_constraints_violation(일반 커널) 또는 reflex. 미확정.
- bringup이 죽으면 새 controller_manager에는 fr3_arm_controller가 없으므로 spawner부터 다시 필요(사용자 혼란 원인).
- 운영 규칙: 움직이기 직전 activate, 끝나면 즉시 deactivate. bringup은 `2>&1 | tee ~/bringup_$(date +%H%M).log`로 실행해 원인 확보.
- 배경: snapd-desktop-integration 2초 주기 재시작 루프(880회+) 관측. 손대지 않음.
- 사용자 선호: 명령은 코드블록 하나당 하나 + 한 줄 설명(노션 정리용). 설명은 원리 위주로, 직접 실행하며 이해하고 싶어 함.

## 2026-10-07 (Claude)

- 새 패키지 src/fr3_skills (ament_python): motion.py의 Fr3Motion(현재 관절 이름 매핑, MoveGroup 계획, 계획 요약, 컨트롤러 active 확인 후 ExecuteTrajectory, scaling 상한 0.2), `ros2 run fr3_skills move_home [--execute] [--scaling]`. HOME = config/poses.yaml = SRDF ready. 실물 미검증.
- fake hardware(도메인77)로 계획/실행거부/scaling 거부 확인. 테스트 프로세스 정리.
- 합의한 구조: ①드라이버 ②fr3_skills ③perception/calibration ④bin_picking 상태머신. 카메라 전에 가짜 물체 좌표로 ④ 먼저.
- 사용자가 더 큰 노트북(ROS 기반)으로 실물 제어까지 이전 희망. 이전 묶음 ~/fr3_migration_20261007.tar.gz(28K) 생성: migration/MIGRATION_KO.md(단계별 가이드), franka_ros2_local_changes.patch(v2.0.2 깨끗한 checkout에 git apply --check 통과), fr3_skills, scripts, 문서 3개. 원본 패키지는 같은 태그로 재clone. 새 노트북 사양(Ubuntu/ROS 버전, 이더넷) 미확인.
- 이후 GitHub 비공개 저장소 https://github.com/yezin293/franka_ros2_ws 로 전환(사용자가 직접 push). 압축 묶음 대신 clone → vcs import --recursive src < fr3.repos → 패치 적용. 운영: git pull → 작업 → commit → push. 원본 패키지는 .gitignore, franka_ros2 수정 시 migration/ 패치 재생성 필요.

## 2026-10-07 오후 (새 노트북 NUC11PHi7, Claude)

위 절(마이그레이션 패키지 작성, GitHub 전환)에 이어 실제로 새 노트북에서 GitHub 저장소를 clone하고 환경을 처음부터 구성해 실물 재현까지 완료했다. 새 노트북 식별: hostname `wynz-NUC11PHi7`, 계정 `wynz`, 워크스페이스 `/home/wynz/franka_ros2_ws`, 이더넷 `enp89s0`(기존 `enp129s0`와 다름).

### 환경 특이사항: conda 자동 활성화

이 노트북은 miniconda3가 설치돼 있고 `.bashrc`의 `conda init` 블록이 **모든 새 쉘에서 base 환경을 자동 활성화**한다. ROS Humble은 시스템 python3.10을 기대하는데 conda의 python3(3.13, numpy 없음)가 PATH에서 먼저 잡혀 아래 빌드 실패의 원인이 됐다. **아직 비활성화하지 않았다** — 매 빌드/실행 세션마다 `export PATH=/usr/bin:$PATH`로 우회 중. `conda config --set auto_activate_base false`로 영구 해결할지는 사용자 결정 대기.

### 1. 저장소 받기 + 원본 패키지 (MIGRATION_KO.md 2~4단계)

- `git clone` 완료 상태에서 시작(사용자가 직접 수행). `vcs import --recursive src < fr3.repos`로 libfranka/franka_ros2/franka_description/olvx_descriptions_module 4개 수신.
- `git -C src/franka_ros2 apply migration/franka_ros2_local_changes.patch` 정상 적용 확인(`git status --short`: M 4개 + 새 파일 1개, 가이드 예상과 일치).
- `rosdep install --from-paths src --ignore-src -r -y`는 sudo 비밀번호 입력이 필요해 에이전트가 비대화형으로 실행 불가. 사용자가 본인 터미널에서 직접 실행해 성공.

### 2. 빌드 실패 원인: conda python3 + 캐시된 CMakeCache.txt

- 첫 `colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release` 시도에서 `libfranka`가 CMake 단계부터 실패: `eigenpy`(pinocchio 의존)가 "Failed to detect numpy".
- 원인 1: `which python3`가 `/home/wynz/miniconda3/bin/python3`(numpy 미설치)를 가리킴. `conda deactivate`는 비대화형 서브쉘에서 conda 쉘 함수가 로드되지 않아 효과 없음.
- 원인 2: `export PATH=/usr/bin:$PATH`로 우회해도 재발 — **이전 실패 시도가 만든 `build/` 디렉터리의 CMakeCache.txt가 conda python 경로를 그대로 캐시**하고 있어서 PATH를 바꿔도 반영 안 됨.
- 해결: `rm -rf build install log`로 캐시 제거 + `colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DPYTHON_EXECUTABLE=/usr/bin/python3 -DPython3_EXECUTABLE=/usr/bin/python3` (PATH도 `/usr/bin` 우선). **16개 패키지 전부 빌드 성공**(경고만 있음: pinocchio/boost python310 헤더 경고, strict-aliasing 테스트 코드 경고 — 기존 노트북 빌드 로그에도 있던 것과 유사한 수준, 실패 아님).

### 3. rtprio 설정: PAM만으로는 부족, systemd user@.service가 별도로 0을 고정

- `/etc/security/limits.d/99-franka-research.conf`(`wynz soft/hard rtprio 99`)를 사용자가 직접 작성. `/etc/pam.d/gdm-password`에 `pam_limits.so` 포함 확인. 그런데 **로그아웃→재로그인을 여러 번 해도 `ulimit -r`이 계속 0**이었다.
- 원인: GNOME 데스크톱 세션의 터미널은 모두 `user@1000.service`(systemd 사용자 매니저, `systemctl show user@1000.service -p LimitRTPRIO` → 0)의 자식 프로세스다. 이 서비스는 `/etc/security/limits.d`를 상속받지 않고 systemd 자체 기본값(0)으로 뜨며, **단순 로그아웃/재로그인으로는 재시작되지 않고** 부팅 이후 계속 살아있어서(확인: `ActiveEnterTimestamp`가 가장 최근 로그인보다 앞섬) PAM 설정이 반영될 기회가 없었다.
- 해결: `/etc/systemd/system/user@.service.d/rtprio.conf` 드롭인에 `[Service]` / `LimitRTPRIO=99` 추가 → `systemctl daemon-reload` → **재부팅**(로그아웃만으론 `user@.service`가 안 재시작돼 불충분, 실제로 재부팅 전까지 반영 안 됐음). 재부팅 후 `ulimit -r` = 99, `systemctl show user@1000.service -p LimitRTPRIO` = 99 확인.
- 이 증상은 기존(2026-10-01) 노트북 인수인계 기록에는 없던 것. 데스크톱 환경/systemd 버전 차이로 추정되며 근본 원인은 더 조사하지 않았다. **다른 컴퓨터로 또 이전할 경우 이 systemd 드롭인도 같이 필요할 수 있음 — MIGRATION_KO.md에 반영 안 돼 있음.**

### 4. 네트워크 + FCI

- `nmcli connection add type ethernet ifname enp89s0 con-name franka-direct ipv4.method manual ipv4.addresses 172.16.0.10/24 ipv4.never-default yes ipv6.method disabled connection.autoconnect yes connection.autoconnect-priority 100` 사용자가 직접 실행, 성공.
- `ping -c3 172.16.0.2` 3/3 성공, 사용자가 Desk에서 Activate FCI 완료.

### 5. 실물 Plan/Execute 재현 성공 (새 노트북 최초)

- fake hardware bringup으로 먼저 빌드/실행 체인 검증: `joint_state_broadcaster` active, controller_manager FIFO 98 RT 스레드로 뜸, "No real-time kernel detected" 경고는 기존과 동일(무시 가능, RT 커널 아님은 알려진 상태).
- 실물 bringup(`franka.launch.py robot_ip:=172.16.0.2 arm_id:=fr3 use_fake_hardware:=false load_gripper:=false`, 사용자가 직접 실행): `joint_state_broadcaster` + `franka_robot_state_broadcaster` active, `/franka/joint_states` 약 1000Hz로 수신. 관절 이름 순서가 이번에도 `fr3_joint1,3,6,7,2,4,5`로 뒤섞여 있음(기존 노트북과 동일 패턴 재확인, name 매핑 원칙 유효).
- MoveIt: 처음에 `execute` 인자 없이 띄웠다가 Execute 안 되는 구조임을 설명하고, `move_group.launch.py robot_ip:=172.16.0.2 load_gripper:=false execute:=true`로 재실행. RViz fr3_arm Plan 성공.
- 실행 연결: `ros2 run controller_manager spawner fr3_arm_controller --inactive -p .../fr3_arm_controller_real.yaml` → 움직이기 직전 `ros2 control set_controller_state fr3_arm_controller active` → RViz **Execute 성공**(사용자 확인) → 즉시 `... inactive`로 전환.
- **`ros2_control_node` 크래시 없음** — 기존 노트북에서 2회 있었던 abort(-6, 44초/86초 후)가 이 세션에서는 재발하지 않음. 장시간 검증은 아니고 원인은 여전히 불명이므로 "해결"로 기록하지 않는다. 운영 규칙(움직이기 직전 activate, 끝나면 즉시 deactivate)은 계속 유지.

### 6. fr3_skills `move_home` 최초 실물 검증

- `src/fr3_skills`(2026-10-07 오전 작성 시점엔 "실물 미검증" 상태)의 `move_home`을 이번에 **처음으로 실물에서 검증**했다.
- HOME 포즈 확인: `fr3_skills/config/poses.yaml`의 `home` 값은 `src/franka_description/robots/common/group_definition.xacro`(Franka Robotics 공식 `franka_description` 패키지)의 SRDF `group_state name="ready"`를 그대로 복사한 것(joint1=0, joint2=-π/4, joint3=0, joint4=-3π/4, joint5=0, joint6=π/2, joint7=π/4). 임의로 만든 값이 아니라 Franka 공식 "ready" 기준 자세.
- 실행 전 plan-only로 먼저 확인: 당시 현재 자세 기준 최대 변화는 joint4 약 0.437rad(≈25°), joint6 약 0.322rad(≈18.5°), 나머지는 더 작음, 총 1.93초 궤적. 주변 충돌 여지 확인 후 진행.
- 순서: controller active → `ros2 run fr3_skills move_home --execute` → controller inactive. **사용자 확인으로 성공**. `poses.yaml`의 "Not yet verified on the real robot" 주석은 이제 사실과 다르므로 다음 작업 때 갱신 필요.

### 7. 사용자가 제시한 다음 목표

카메라 연결/인식은 여전히 맨 마지막 순서. **사용자가 새로 제시한 다음 목표: 물체의 위치(pose)를 토픽으로 publish하면 로봇이 그 위치까지 자동으로 이동.** 아래 절에서 같은 날 바로 구현/검증했다.

## 2026-10-07 저녁 (Claude) — move_to_pose + pose_listener 구현 및 실물 검증

### 설계 결정

- pose 입력은 `geometry_msgs/PoseStamped` (표준, 사용자 동의).
- 실행 방식은 `move_home`과 동일한 패턴: `pose_listener`(plan만, 기본값) / `pose_listener --execute`(실제 이동)로 모드를 나눔. 처음엔 "자동 Execute"와 "확인 후 Execute" 사이에서 논의했으나, 코드 자체를 두 모드로 다 만들어두고 사용자가 상황에 맞게 플래그로 고르는 쪽으로 정리됨. plan 결과는 RViz의 `/move_group/display_planned_path` 구독(MotionPlanning 패널)으로 어차피 자동 시각화되므로, RViz로 보고 판단한 뒤 필요하면 `--execute`로 재시작하는 흐름이 가능.

### 구현

- `fr3_skills/motion.py`: `plan_to_pose(pose_stamped, scaling, tolerance_m=0.01, tolerance_rad=0.01)` 추가. `PositionConstraint`(SPHERE 반경 tolerance_m) + `OrientationConstraint`로 목표 pose 그대로 제약 구성, EE_LINK(`fr3_link8`, load_gripper:=false 전제)에 적용. 기존 `plan_to_joints`(조인트 목표)와 별개로 공존.
- `fr3_skills/pose_listener.py` 신규: `/object_pose`(토픽명 `--topic`으로 변경 가능) 구독 → 들어올 때마다 `plan_to_pose` → `describe` 출력 → `--execute`면 `execute`까지. `setup.py`에 콘솔 스크립트 등록.
- pose의 `header.frame_id`를 그대로 신뢰(하드코딩 안 함). RViz/MoveIt의 planning/fixed frame은 `fr3_link0`(`moveit.rviz`에서 확인) — 테스트 시 이 프레임으로 publish.

### 버그: 콜백 안에서 rclpy.spin_once 중첩 호출

- 첫 버전은 `rclpy.spin(motion)`을 메인 루프로 쓰고, 그 안의 구독 콜백에서 `motion.current_joints()`(내부적으로 `rclpy.spin_once` 반복)를 호출하는 구조. 실행하자마자 "stopped: no /franka/joint_states (is bringup running?)"로 실패.
- bringup은 실제로 정상(컨트롤러 3개 모두 active, `/franka/joint_states` 1000Hz 확인)이었음. 원인은 **이미 실행 중인 `rclpy.spin()`의 실행기(executor) 안에서, 그 콜백이 다시 `rclpy.spin_once()`를 호출하는 중첩** — rclpy의 전역 실행기가 재귀적으로 꼬여서 새 메시지를 못 받아 타임아웃.
- `move_home.py`는 이런 중첩이 없어 문제 없었음(해당 스크립트는 `rclpy.spin()`을 아예 안 쓰고 필요한 곳에서만 `spin_once`/`spin_until_future_complete`를 직접 호출).
- 해결: `pose_listener.py`의 구독 콜백은 메시지를 리스트에 저장만 하고 끝냄(`pending.append`). 실제 처리(관절 조회/계획/실행)는 메인 루프가 `rclpy.spin_once(motion, timeout_sec=0.1)`를 **콜백 바깥에서** 반복 호출하는 중에 수행하도록 재작성. 중첩 제거 후 정상 동작.

### 실물 검증

- fake 테스트 pose(x=0.4, y=0.0, z=0.4, 방향 identity, frame `fr3_link0`)로 plan-only 모드 확인: 70 포인트, 6.86초 궤적, joint1이 약 -1.52rad 크게 회전(임의로 고른 테스트 좌표라 그런 것, 실제 목표에선 다를 수 있음). RViz에도 경로 표시 확인.
- `fr3_arm_controller` active 상태로 `pose_listener --execute` 실행 → 같은 pose publish → **실물이 목표 위치로 자동 이동** (사용자 확인: "잘 돼"). 이후 `ros2 control set_controller_state fr3_arm_controller inactive`로 복귀, 운영 규칙 유지.
- `fr3_skills/config/poses.yaml`의 home 주석을 "실물 검증 완료(2026-10-07)"로 갱신 완료.

### 알려진 한계 (다음에 다룰 것)

- **작업영역/안전 범위 검사 없음.** 지금은 들어온 pose가 테이블/3030 프로파일 밖이거나 이상한 값이어도 MoveIt의 IK/충돌 체크(충돌 모델이 팔만 있고 Hand/테이블 전체는 빠져 있을 수 있음, 위 "현장 사진과 안전 범위" 절 참고)만 통과하면 그대로 실행됨. 좌표 범위 제한을 pose_listener나 motion.py 쪽에 추가해야 함.
- `EE_LINK = 'fr3_link8'`는 `load_gripper:=false`일 때만 맞음. 나중에 Hand를 모델에 포함시키면 TCP 링크명을 다시 확인하고 바꿔야 함(아마 `fr3_hand_tcp` 계열).
- 방향(orientation) 허용오차 0.01rad, 위치 허용오차 0.01m을 임의로 정함 — 실제 요구 정밀도에 따라 조정 필요.
- `--execute` 모드는 pose가 들어올 때마다 바로 실제로 움직인다. 지금은 사람이 수동으로 pose를 publish하며 테스트 중이라 괜찮지만, 카메라 연동 후 자동 pose 발행이 붙으면 이 알려진 한계(안전 범위 없음)가 더 중요해짐.

## 2026-10-08 (Claude) — 그리퍼 실물 검증 + RViz 연동 + 팔/그리퍼 제어 통합

### 1. RViz에서 그리퍼(hand group) Execute 연동

- `franka_fr3_moveit_config/launch/move_group.launch.py`를 고쳐서, `load_gripper:=true`일 때만 `moveit_controllers`에 그리퍼 컨트롤러를 추가하도록 `OpaqueFunction`으로 재구성(런타임에 `load_gripper` 값을 보고 조건부로 딕셔너리 구성). `load_gripper:=false`일 때는 기존과 동일(팔만).
- **버그 발견 및 수정**: 원본 Franka 공식 `fr3_controllers.yaml`은 그리퍼 MoveIt 컨트롤러 이름을 `fr3_gripper`로 적어놨는데, 실제 떠 있는 그리퍼 노드 이름은 `franka_gripper`(`franka_gripper/launch/gripper.launch.py` 참고)라 이름이 안 맞았음. 이 불일치는 예전부터 문서에 "미해결"로 기록돼 있던 이슈. 우리 launch의 매핑 키를 실제 노드명(`franka_gripper`)으로 맞춰서 해결. (주의: 이건 우리 `move_group.launch.py`에만 적용된 수정이고, 원본 `fr3_controllers.yaml` 파일 자체나 통합 `moveit.launch.py` 쪽은 그대로임 — 그쪽을 쓰면 여전히 같은 문제 재발함.)
- 설치 디렉터리는 소스 symlink라 재빌드 불필요.

### 2. 그리퍼 최초 실물 검증

- bringup/MoveIt을 `load_gripper:=true`로 재시작 후 `/franka_gripper` 노드와 액션 4개(`homing`/`move`/`grasp`/`gripper_action`) 확인.
- **Homing 1차 시도 실패**: `libfranka gripper: Command failed!`, 손가락이 끝까지 안 열리고 중간(폭 약 6.3mm)에서 멈춤. 사용자가 손가락 주변 장애물 확인 후 재시도 → **성공**(완전 개방, 각 손가락 0.04m = 전체 80mm). 원인은 안 찾음(장애물이었는지 일시적 오류였는지 불명) — 다음에 또 실패하면 같은 방식(장애물 확인 → 재시도)으로 대응.
- `Move` 액션으로 폭 0.02m 이동 테스트 성공(각 손가락 0.01m로 정확히 도달).
- RViz MotionPlanning 패널에서 Planning Group을 `hand`로 바꿔서 Plan+Execute(open/close) 성공(사용자 확인). **단, 같은 세션에서 `fr3_arm_controller`를 spawner로 다시 로드하기 전까지는 팔 쪽 Execute가 안 됨** — bringup을 그리퍼 포함해서 새로 켜면 팔 컨트롤러도 새로 spawn해야 하는 걸 깜빡해서 한 번 헤맴. bringup 재시작마다 spawner 필요함을 재확인.

### 3. 팔 제어 + 그리퍼 제어를 한 클래스로 통합, activate/deactivate 자동화

사용자가 "팔 따로 그리퍼 따로 말고 터미널에서 하나로 할 수 없냐"고 요청 → `fr3_skills/motion.py`의 `Fr3Motion`에 아래 추가:

- `activate_arm()` / `deactivate_arm()`: `/controller_manager/switch_controller` 서비스로 `fr3_arm_controller`를 켜고 끔(이미 원하는 상태면 아무 것도 안 함). 지금까지 터미널에서 직접 치던 `ros2 control set_controller_state ...`를 코드 안으로 옮긴 것.
- `home_gripper()` / `open_gripper(width, speed)` / `close_gripper(speed)` / `grasp(width, speed, force, epsilon_inner, epsilon_outer)`: `franka_msgs/action/{Homing,Move,Grasp}` 액션 클라이언트. `ros2 action send_goal /franka_gripper/...`로 하던 걸 같은 클래스 메서드로.
- `pose_listener.py`와 `move_home.py`의 `--execute` 모드가 이제 **움직이기 직전에 `activate_arm()`, 끝나면(예외 나도) `finally`에서 `deactivate_arm()`**을 스스로 호출함. 사용자가 별도로 `ros2 control set_controller_state` 명령을 칠 필요 없어짐. "active로 계속 켜두지 말고 움직일 때만 켠다"는 기존 안전 규칙은 그대로 유지 — 자동화만 된 것이고 상시 active로 바꾼 게 아님(과거 ros2_control_node abort 이력 때문에 상시 active는 권장하지 않기로 함, 사용자에게 설명 후 동의받음).
- `package.xml`에 `franka_msgs`, `geometry_msgs`, `shape_msgs` exec_depend 추가.

### 실물 검증

- `close_gripper()` → `open_gripper()`를 파이썬에서 직접 호출해 정상 동작 확인.
- `pose_listener --execute`로 테스트 pose 재전송: **자동으로 activate → 6.64초 궤적 실행 → deactivate**까지 사람이 컨트롤러 명령 한 번도 안 치고 끝까지 완료됨. `ros2 control list_controllers`로 끝난 후 `fr3_arm_controller`가 다시 inactive인 것 확인.

### 4. 작업영역 안전 범위 — z 체크 + 테이블 충돌 객체

사용자: "엔드 이펙터가 로봇 베이스 기준 z=0만 아니면 부딪힐 일 없다" → 처음엔 목표점 z만 체크했는데, 사용자가 "어느 관절이든 z<0 금지가 낫지 않냐"고 제안 → MoveIt 충돌 검사를 활용하는 쪽으로 변경.

- `plan_to_pose()`에 두 가지 선행 체크 추가: ①`pose_stamped.header.frame_id`가 `BASE_FRAME`(`fr3_link0`)이 아니면 거부(아래 z 체크가 이 프레임을 전제하므로), ②목표 z < `MIN_Z`(0.0)면 거부. 빠르고 명확한 1차 방어선(목표점만 체크).
- `Fr3Motion.ensure_table_collision()` 추가: `/apply_planning_scene` 서비스로 `table_floor`라는 `CollisionObject`(BOX)를 플래닝 씬에 등록. 이후 MoveIt의 충돌 검사가 **팔의 어느 링크든**(엔드 이펙터뿐 아니라 팔꿈치/어깨까지) 이 박스에 닿는 계획을 자동으로 거부함 — 목표점 체크보다 훨씬 포괄적인 보호.
- 실제 테이블 치수(600×600×800mm 프로파일, 사용자가 이전에 알려준 값) 반영: 박스 크기 0.6×0.6×0.8m. 위치는 "베이스가 정사각형 한 변 중앙에, 베이스 뒷면부터 고정"이라는 설명에 따라 `fr3_link0` 원점에서 **+X 방향(로봇이 보는 정방향, 사용자 확인됨)으로 0~0.6m, Y는 -0.3~0.3m(중앙), Z는 0~-0.8m(바닥까지)**로 배치. 처음엔 과도하게 큰 3m×3m 박스로 임시 구현했다가 사용자가 실제 치수로 고치라고 지적해서 수정.
- `pose_listener.py`/`move_home.py`가 시작할 때 `motion.ensure_table_collision()`을 자동으로 호출하도록 연결.
- 실물 검증: `/get_planning_scene` 서비스로 `table_floor` 객체가 정확한 크기(0.6,0.6,0.8)와 위치(x=0.3, y=0, z=-0.4, 즉 중심점)로 등록된 것 확인. z<0 목표 pose(z=-0.1) 전송 시 `plan_to_pose`에서 즉시 거부되는 것도 별도로 확인(z=0.4는 정상 plan됨).
- **한계**: 테이블에 아직 상판이 없다는 기존 기록(상판 추후 설치 예정)과 무관하게, 프로파일/아래 상자/케이블 등 위험요소를 포괄적으로 막기 위해 "그 공간은 통째로 막혀있다"고 가정한 박스임 — 실제 빈 공간이라도 로봇이 들어가지 않게 보수적으로 설정한 것. 테이블 밖(이 박스 바깥) z<0은 `MIN_Z` 체크가 여전히 전체적으로 막음.

### 5. 그리퍼 터미널 CLI + move_home에 그리퍼 통합, 환경 설정 관련 정정

- 신규 `fr3_skills/gripper.py` → `ros2 run fr3_skills gripper --home|--open|--close|--move WIDTH|--grasp WIDTH [--speed] [--force]`. `motion.py`의 `home_gripper`/`open_gripper`/`close_gripper`/`grasp`를 터미널에서 바로 쓰게 만듦(이전엔 메서드만 있고 CLI가 없어서 여전히 `ros2 action send_goal /franka_gripper/...`를 길게 쳐야 했음 — 사용자가 "왜 자꾸 따로따로 하냐"고 지적해서 추가).
- 사용자 요청: **"홈 자세 = 팔 홈 + 그리퍼 열림"**으로 재정의. `move_home.py`의 `move_home()`이 팔 execute 성공 후 자동으로 `motion.open_gripper()`까지 호출. **이제 `move_home --execute`는 `load_gripper:=true`로 띄운 bringup이 전제**임(그리퍼 없으면 마지막 open 단계에서 에러). 실물에서 "팔 홈 이동 + 그리퍼 열기"까지 한 줄로 성공 확인(사용자: "엉 햇어 잘됨").
- **환경 설정 관련 정정 2건** (사용자 질문으로 바로잡음):
  1. `export PATH=/usr/bin:$PATH`는 **`colcon build` 때만 필요**, `ros2 run`/`ros2 launch` 등 실행에는 불필요. 이유: `ros2`나 `fr3_skills`의 설치된 실행 파일들은 shebang이 `#!/usr/bin/python3`로 고정돼 있어 `$PATH`와 무관하게 항상 `/usr/bin/python3`를 씀(conda가 PATH 맨 앞에 끼어들어도 영향 없음). 반면 `colcon build`의 CMake 단계는 `$PATH`에서 `python3`를 찾아 쓰기 때문에(eigenpy의 FindNumpy 등) conda 문제가 생겼던 것 — 그래서 빌드할 때만 PATH 우회/`-DPYTHON_EXECUTABLE` 필요.
  2. `source /opt/ros/humble/setup.bash`도 매번 손으로 안 쳐도 됨 — `~/.bashrc`에 이미 자동으로 들어가 있음(124번째 줄). 새 터미널 열면 자동 적용.
  - 터미널 가이드(사용자가 Notion에 복붙한 버전)에서 이 두 줄을 빼야 함 — 혹시 다음에 또 가이드 만들 때 반영.

## 2026-10-08 오후~저녁 (Claude) — pick/place 구현, 실물 충돌 사고·복구, 테이블 충돌 모델 정밀 보정

### 1. pick/place 구현과 TCP 링크 문제

- `motion.py`에 `pick(pose, approach_height, width, speed, force, scaling)` / `place(pose, approach_height, speed, scaling)` 추가 — 접근→(pick만)그리퍼 열기→하강→그립/놓기→후퇴를 한 번에, 내부에서 `activate_arm`/`deactivate_arm` 자동 처리.
- 실제 집는 지점은 `fr3_link8`(팔 플랜지)이 아니라 **`fr3_hand_tcp`**(손가락 접촉점, link8에서 0.1034m 더 나감 — franka_description `end_effectors/common/franka_hand.xacro`의 `tcp_xyz` 공식값)여야 함을 확인하고 `TCP_LINK` 상수로 분리.
- **버그**: `fr3_hand_tcp`를 `plan_to_pose`의 `link_name`으로 직접 주면 `GOAL_STATE_INVALID(-27)` — `fr3_arm` 그룹의 IK 솔버가 `fr3_link8`(그룹의 tip_link)만 풀 수 있어서 다른 링크는 IK 자체가 안 됨. 해결: `_tcp_pose_to_ee_pose()`로 목표 TCP pose를 수학적으로 link8 pose로 변환(쿼터니언 직접 계산, 위치는 TCP 방향의 로컬 -Z로 0.1034m 이동 + yaw 보정 Rz(+45°))해서 기존 link8 IK 경로를 그대로 씀. 단위 테스트로 변환식 검증 완료.
- `pick_place.py` CLI 추가 (`ros2 run fr3_skills pick_place --pick x y z --place x y z [--width] [--force] [--approach-height]`).

### 2. 실물 충돌 사고와 복구

- `pick_place`를 z=0.3(비교적 높은 안전 지점으로 판단)로 백그라운드 테스트하던 중, **손목/전완 관절이 테이블 프로파일 레일에 접촉 → 사용자가 비상정지**. 그리퍼 자체가 아니라 다른 관절이었음 — "목표점은 안전해도 그 자세로 가는 동안 다른 링크가 z=0보다 위에 있는(기존 모델엔 없던) 구조물에 닿을 수 있다"는 걸 실물로 확인한 사건.
- Desk에서 Lock→Unlock 해도 "Configured force thresholds reached"가 바로 재발 — 접촉이 안 떨어진 채로 unlock을 시도하니 유지 토크가 바로 임계값을 넘겨서 재발동. 공식 매뉴얼상 정식 복구는 External Enabling Device(펜던트) + Recovery 다이얼로그 +/- 버튼인데 **펜던트가 없어서** 이 경로는 못 씀.
- 최종적으로 사용자가 재부팅 후 unlock되는 흰색(hand-guidable) 순간에 **손으로 재빨리 팔을 들어 접촉을 떼어내서 해결**. 이후 End Effector "Not connected"로 떴던 것도 별다른 조치 없이 복구됨(원인/정확한 복구 시점 불명, 재발 시 참고).
- 복구 과정에서 bringup(터미널1)도 멈춰있었던 적 있음 — 재시작 필요.
- **교훈**: 외부 인에이블링 장치가 이 연구실엔 아직 없음(확인 필요 — 담당 교수님 연구실 또는 Franka 공식 지원팀에 문의 권장, 다음에 또 이런 상황 나면 복구 수단이 제한적임).

### 3. `move_group.launch.py` joint_states 리맵 버그

- `load_gripper:=true`로 띄워도 `joint_states` 토픽이 항상 `franka/joint_states`(팔 전용)로 고정 리맵돼 있어서, move_group이 그리퍼 조인트 상태를 영원히 못 보고 "Missing fr3_finger_joint1" 경고가 계속 남. `load_gripper` 값을 보고 `/joint_states`(팔+그리퍼 병합, `franka_bringup`의 `joint_state_publisher`가 만듦) 로 조건부 리맵하도록 수정.

### 4. 테이블 충돌 모델 정밀 보정 (반복 보정 끝에 확정)

사고 이후 사용자가 "z=0 대신 10cm 위로"를 요청해 `SAFE_Z_MARGIN=0.10`을 박스 윗면(`TABLE_TOP_Z`)과 목표점 체크(`MIN_Z`) 둘 다에 적용했는데, RViz에서 로봇 베이스가 "테이블에 가라앉은" 것처럼 보여 긴 보정 과정을 거침:

- 처음엔 X축 문제로 의심(베이스가 뒤로 더 튀어나와 있음) → **실측으로 확인**: `franka_description/meshes/robot_arms/fr3/collision/link0.stl`을 직접 파싱(파이썬 struct로 바이너리 STL 파싱) — x: -0.153~+0.070, z: 0.000~+0.140. visual mesh(`link0.dae`, COLLADA XML 파싱)도 대조 — x: ±0.095(대칭), z: 0~140(mm, 단위만 다름). **둘 다 z=0이 정확히 베이스 바닥**임을 확인, xacro에 추가 origin 오프셋도 없음 확인(추측 아닌 파일 실측).
- `BASE_BACK_MARGIN=0.16`으로 박스 시작점을 x=-0.16까지 늘려서 베이스 발판 전체(실측 -0.153 기준 여유 포함)를 덮음. 정면(원근 아닌) 스크린샷으로 사용자가 실제와 일치함을 확인("와 이거야 실제로 이렇게 되어있어").
- 그런데 `SAFE_Z_MARGIN=0.10`이 테이블 윗면 자체를 10cm 올려버려서, 베이스 전체 높이(14cm) 중 대부분이 초록 박스에 덮여 시각적으로 이상해 보임 → 사용자가 "10cm 빼고 보자"고 요청, 제거 후 실제 모습과 일치 확인.
- **최종 설계**: `TABLE_TOP_Z=0.0`(실측 그대로, 패딩 없음) 로 테이블 모델은 항상 실제와 정확히 일치하게 유지. 안전 여유는 모델을 부풀리지 않고 **`TARGET_Z_MARGIN=0.03`**(`MIN_Z`)로 분리해서, `plan_to_pose`가 받는 목표 좌표만 z<0.03이면 거부하도록 함. 즉 "모델은 정확하게, 목표점만 보수적으로"로 역할을 나눔. 실물 재등록 + z=0.02 거부 테스트로 검증 완료.
- `fr3_link0`(고정 베이스)와 `table_floor`가 여전히 기하학적으로 겹치는 상태지만, 베이스는 절대 안 움직이고 `FixStartStateCollision` 플래너 어댑터가 이런 사소한 시작 상태 겹침을 자동 보정하는 것으로 보여 별도 AllowedCollisionMatrix 예외 처리는 하지 않기로 함(오늘 여러 번 Plan/Execute 성공으로 간접 확인). 더 깨끗하게 하려면 ACM에 `table_floor`-`fr3_link0` 허용 쌍을 추가할 수 있음(리스크: 기존 ACM을 잘못 덮어쓰면 다른 충돌 검사가 깨질 수 있어 신중해야 함, 아직 안 함).

## 2026-10-12 (Claude) — Cartesian path로 하강/후퇴 직선화, pick/place 실물 검증 성공

4일 만에 재개. 세션 시작하자마자 확인한 것: **지난번(10/8) 작업이 로컬에 저장만 되고 Git 커밋이 안 된 상태**였음(`git status`로 확인, `motion.py`/`pose_listener.py`/`gripper.py`/`pick_place.py` 등 다수가 수정됨(M)/추적안됨(??) 상태). 아직 커밋/푸시 안 함 — 사용자에게 알렸고 다음에 요청 시 처리.

### 1. 테이블 모델 세션 간 지속성 확인

- 코드(`motion.py`)에 10/8 확정값(테이블 박스 x:-0.16~0.6/y:-0.3~0.3/z:-0.8~0, `MIN_Z=0.03`)이 그대로 저장돼 있음을 확인.
- **중요한 운영 사실 재확인**: 충돌 박스는 move_group을 껐다 켤 때마다(즉 세션마다) **플래닝 씬이 초기화**돼서 사라짐 — `ensure_table_collision()`을 다시 호출해야 함(`pose_listener`/`move_home`/`pick_place`는 시작할 때 자동으로 부름). RViz로 실제와 대조 재확인("아주 정확해 실제로 딱 이런 구조").
- MoveIt이 실제로 팔 전체를 보호하는지 직접 검증: `MIN_Z` 파이썬 가드를 임시로 우회하고 테이블 박스 깊숙한 곳(z=-0.3)과 표면 바로 아래(z=-0.05) 둘 다 `plan_to_pose`에 직접 요청 → 둘 다 MoveIt이 거부(`GOAL_STATE_INVALID`) 확인. 목표점 체크뿐 아니라 MoveIt 자체 충돌 검사가 실제로 동작한다는 걸 실측으로 증명.

### 2. pick/place에 plan-only(dry-run) 모드 추가

- 기존 `pick()`/`place()`는 안전장치 없이 바로 `activate_arm()`+`execute()`까지 가던 구조였음(10/8 사고 이후인데도 빠뜨림) — `dry_run=True` 파라미터 추가: 각 구간(approach/descend/retreat)을 plan만 하고 터미널에 출력 + RViz에 자동으로 보임(move_group이 모든 plan을 `/move_group/display_planned_path`에 쏘기 때문), activate/execute/그리퍼 호출은 전혀 안 함.
- `pick_place.py` CLI에 `--execute` 플래그 추가 — **기본값이 이제 plan-only**(`move_home`/`pose_listener`와 동일한 패턴으로 통일).

### 3. 기본 방향을 "아래로 향하게"로 변경

- `pick_place.py`의 `make_pose()`가 orientation identity를 기본값으로 쓰고 있었는데, 테스트해보니 이 방향은 테이블 근처 목표에서 **거의 항상 IK 불가**(`GOAL_STATE_INVALID`)였음. identity는 TCP의 z축이 위를 향하는 방향이라 물건을 집기엔 안 맞는 자세였음.
- roll 180°(쿼터니언 x=1, w=0, TCP z축이 아래를 향함)로 바꾸니 바로 reachable. 기본값을 이걸로 변경.

### 4. 손목이 꼬이는 문제 → Cartesian path로 해결

- 사용자가 RViz에서 descend/retreat 중 손목이 불필요하게 꼬이는 걸 관찰 → 원인: OMPL(RRTConnect)은 시작/끝 자세만 제약하고 중간 경로는 샘플링이라, "똑바로 내려가기" 같은 직선 동작에는 안 맞음(연구/산업 표준도 이런 구간엔 Cartesian path를 씀, 자유공간 이동만 OMPL).
- `Fr3Motion.plan_cartesian_path()` 신규 추가 — `/compute_cartesian_path` 서비스로 직선 경로 계산. **확인된 사실**: 이 서비스가 반환하는 trajectory에 이미 실제 속도/시간 프로파일이 들어있음(빈 웨이포인트 나열이 아니라 진짜 실행 가능한 trajectory) — 직접 호출해서 `time_from_start`/`velocities` 찍어보고 확인(2026-10-12). 단, 이 서비스엔 속도 스케일링 입력이 없어서, 반환된 trajectory를 "시간을 1/scaling배 늘리고 속도를 scaling배 줄이는" 균일 재조정(`_retime()`)으로 기존 `scaling` 관례와 맞춤.
- **버그 1차**: Cartesian용 `scaling`에 OMPL용 `MAX_SCALING=0.2`를 그대로 재사용했다가, 기본 `scaling=0.1`을 그대로 넣으니 10cm 하강이 23초나 걸림(원래 자연스러운 속도가 이미 적당한 수준인데 그걸 또 10배 늦춘 것). **해결**: `CARTESIAN_MAX_SCALING=1.0`을 별도로 두고, `pick`/`place`에 `cartesian_scaling=1.0` 기본값을 분리(`scaling`은 approach 구간의 OMPL에만 적용). 재시험 결과 descend/retreat 모두 2~2.5초로 자연스러운 속도.
- `pick()`/`place()`의 descend/retreat 구간을 `plan_cartesian_path`로 교체(approach는 자유이동이라 OMPL 유지).

### 5. 실물 pick/place 성공

- plan-only로 6단계(pick: 접근→하강→집기, place: 접근→하강→놓기) 전부 확인 후, `--execute`로 실물 테스트 → **성공**(사용자: "아주 잘갔오 다행이다"). 10/8 사고 이후 pick/place의 첫 실물 성공.

### 다음에 할 일 (Claude)

1. **Git 커밋/푸시 아직 안 함** — 10/8 이후 전체 작업(테이블 모델, pick/place, gripper CLI, Cartesian path 등)이 로컬에만 있음. 다음에 요청 들어오면 처리.
2. Bin Picking 상태머신 뼈대 — 카메라 전까지는 가짜(수동 publish) 물체 좌표로 검증. pick/place가 이제 실물 검증까지 끝났으니 바로 조립 가능.
3. 외부 인에이블링 장치(펜던트) 확보 여부 확인 — 없으면 다음 비상정지/충돌 시 Desk 공식 복구 절차를 못 씀. 담당 교수님 연구실 또는 Franka 지원팀 문의 권장.
4. conda 자동 활성화 영구 비활성화 여부 결정 대기 — 실행에는 영향 없고 빌드에만 영향이라 긴급하지 않음.
5. migration/MIGRATION_KO.md의 패치 재생성 필요 — franka_ros2(`move_group.launch.py`)를 여러 번 더 수정해서 `migration/franka_ros2_local_changes.patch`가 최신 상태와 크게 어긋남. systemd `user@.service` rtprio 드롭인 단계도 아직 반영 안 됨.
6. 카메라는 여전히 맨 마지막 순서.
