*** Settings ***
Library    SSHLibrary

*** Variables ***
${ADMIN_USER}        admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}         ${EMPTY}
${TEST_FQDN}         qbittorrent.test.local
${BT_PORT}           26881

*** Keywords ***
Login to cluster-admin
    New Page    https://${NODE_ADDR}/cluster-admin/
    Fill Text    text="Username"    ${ADMIN_USER}
    Click    button >> text="Continue"
    Fill Text    text="Password"    ${ADMIN_PASSWORD}
    Click    button >> text="Log in"
    Wait For Elements State    css=#main-content    visible    timeout=10s

*** Test Cases ***
Check if qbittorrent is installed correctly
    ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Check if qbittorrent can be configured
    # The module requires a virtual host: an empty payload is rejected by
    # the input schema on purpose.
    ${rc} =    Execute Command
    ...    api-cli run module/${module_id}/configure-module --data '{"host":"${TEST_FQDN}","http2https":false,"lets_encrypt":false,"bt_port":${BT_PORT},"bt_port_enabled":true}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if get-configuration reflects the configure-module input
    ${output} =    Execute Command    api-cli run module/${module_id}/get-configuration
    &{config} =    Evaluate    ${output}
    Should Be Equal    ${config.host}    ${TEST_FQDN}
    Should Be Equal As Integers    ${config.bt_port}    ${BT_PORT}
    Should Be True    ${config.bt_port_enabled}
    # An empty downloads_dir means the named volume is in use
    Should Be Equal    ${config.downloads_dir}    ${EMPTY}

Check if invalid settings are rejected
    # A downloads directory that does not exist must fail validation rather
    # than starting a container that cannot save anything.
    ${rc} =    Execute Command
    ...    api-cli run module/${module_id}/configure-module --data '{"host":"${TEST_FQDN}","http2https":false,"lets_encrypt":false,"downloads_dir":"/nonexistent/qbittorrent"}'
    ...    return_rc=True  return_stdout=False
    Should Not Be Equal As Integers    ${rc}  0

Check if the configuration volume is seeded for the reverse proxy
    ${output} =    Execute Command
    ...    runagent -m ${module_id} podman volume inspect --format '{{.Mountpoint}}' qbittorrent-config
    ${conf} =    Execute Command    cat ${output}/qBittorrent/qBittorrent.conf
    Should Contain    ${conf}    WebUI\\ReverseProxySupportEnabled=true
    Should Contain    ${conf}    Session\\Port=${BT_PORT}
    # Authentication must not be bypassed: Traefik connects from 127.0.0.1
    Should Contain    ${conf}    WebUI\\LocalHostAuth=true

Check if the WebUI answers through traefik
    # The module registers a host-based route, so the Host header selects it
    ${rc} =    Execute Command    curl -f -s -o /dev/null -H 'Host: ${TEST_FQDN}' http://127.0.0.1/
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the BitTorrent port is open in the firewall
    ${output} =    Execute Command    firewall-cmd --zone=public --list-ports
    Should Contain    ${output}    ${BT_PORT}/tcp
    Should Contain    ${output}    ${BT_PORT}/udp

Check if disabling the port unbinds it
    # The pod must not publish the port at all when the toggle is off:
    # binding it anyway would block a clone or a migrated instance that
    # deliberately keeps the port closed while another one still holds it.
    ${rc} =    Execute Command
    ...    api-cli run module/${module_id}/configure-module --data '{"host":"${TEST_FQDN}","http2https":false,"lets_encrypt":false,"bt_port":${BT_PORT},"bt_port_enabled":false}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    ${output} =    Execute Command    ss -Hlnt "sport = :${BT_PORT}" ; ss -Hlnu "sport = :${BT_PORT}"
    Should Be Empty    ${output}
    ${ports} =    Execute Command    firewall-cmd --zone=public --list-ports
    Should Not Contain    ${ports}    ${BT_PORT}/tcp

Check if the port is bound again when re-enabled
    ${rc} =    Execute Command
    ...    api-cli run module/${module_id}/configure-module --data '{"host":"${TEST_FQDN}","http2https":false,"lets_encrypt":false,"bt_port":${BT_PORT},"bt_port_enabled":true}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    # Re-applying the same enabled port must not trip the conflict check:
    # our own running pod is the one holding it.
    ${output} =    Execute Command    ss -Hlnt "sport = :${BT_PORT}"
    Should Not Be Empty    ${output}

Check if a port taken by another service is rejected
    # Occupy the candidate port over UDP only: a TCP-only probe would miss it
    Execute Command    (nohup timeout 60 nc -u -l 39999 >/dev/null 2>&1 &) ; sleep 1
    ${rc} =    Execute Command
    ...    api-cli run module/${module_id}/configure-module --data '{"host":"${TEST_FQDN}","http2https":false,"lets_encrypt":false,"bt_port":39999,"bt_port_enabled":true}'
    ...    return_rc=True  return_stdout=False
    Should Not Be Equal As Integers    ${rc}  0

Check if the service can be restarted from the UI action
    ${rc} =    Execute Command    api-cli run module/${module_id}/restart-services --data '{}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    ${output} =    Execute Command    runagent -m ${module_id} systemctl --user is-active qbittorrent-app.service
    Should Be Equal    ${output}    active

Take screenshots
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True
    Login to cluster-admin
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}
    Wait For Elements State    iframe >>> h2 >> text="Status"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/1._Status.png
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=settings
    Wait For Elements State    iframe >>> h2 >> text="Settings"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/2._Settings.png
    Close Browser

Check if qbittorrent is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the firewall port is closed after removal
    ${output} =    Execute Command    firewall-cmd --zone=public --list-ports
    Should Not Contain    ${output}    ${BT_PORT}/tcp
