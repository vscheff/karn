<?php
$socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
$auth = "";
foreach (getallheaders() as $name => $value) if (! strcasecmp($name, "authorization")) { $auth = $value; break; }
$content = file_get_contents("php://input");
socket_connect($socket, "127.0.0.1", "8008");
socket_write($socket, "{\"authorization\": \"$auth\", \"content\": $content}");
socket_close($socket);
?>
