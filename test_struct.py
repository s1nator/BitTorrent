import struct

try:
    s = "test"
    packed = struct.pack("4s", s)
    print("Packed string successfully")
except Exception as e:
    print(f"Failed to pack string: {e}")

try:
    b = b"test"
    packed = struct.pack("4s", b)
    print("Packed bytes successfully")
except Exception as e:
    print(f"Failed to pack bytes: {e}")
