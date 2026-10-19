import rclpy
from rcl_interfaces.srv import GetParameters
from fr3_skills.motion import Fr3Motion
rclpy.init()
node=Fr3Motion()
try:
    client=node.create_client(GetParameters,'/controller_manager/get_parameters')
    if not client.wait_for_service(timeout_sec=5):
        raise RuntimeError('No controller manager')
    future=client.call_async(GetParameters.Request(names=['robot_description']))
    rclpy.spin_until_future_complete(node,future,timeout_sec=5)
    if not future.done() or 'fake_components/GenericSystem' not in future.result().values[0].string_value:
        raise RuntimeError('Verification refuses non-mock hardware')
    start=node.current_joints()
    target=dict(start)
    target['fr3_joint1']+=0.03
    plan=node.plan_to_joints(target,0.1)
    print('FAKE_WITH_TABLE_PLAN',node.describe(plan,start),flush=True)
    node.execute(plan)
    final=node.current_joints()
    error=abs(final['fr3_joint1']-target['fr3_joint1'])
    assert error<0.005,error
    print('FAKE_WITH_TABLE_EXECUTION_OK',error,flush=True)
finally:
    node.destroy_node()
    rclpy.try_shutdown()
