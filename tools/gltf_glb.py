import json
import math
import struct
from pathlib import Path


JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942

COMPONENT_FORMATS = {
    5120: "b",
    5121: "B",
    5122: "h",
    5123: "H",
    5125: "I",
    5126: "f",
}

COMPONENT_SIZES = {
    5120: 1,
    5121: 1,
    5122: 2,
    5123: 2,
    5125: 4,
    5126: 4,
}

TYPE_COUNTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT4": 16,
}


def degquat(rx, ry, rz):
    x = math.radians(rx) * 0.5
    y = math.radians(ry) * 0.5
    z = math.radians(rz) * 0.5

    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)

    return (
        sx * cy * cz + cx * sy * sz,
        cx * sy * cz - sx * cy * sz,
        cx * cy * sz + sx * sy * cz,
        cx * cy * cz - sx * sy * sz,
    )


def pad4(data, byte=b" "):
    padding = (-len(data)) % 4
    return data + byte * padding


class GlbDocument:
    def __init__(self, json_doc, bin_chunk):
        self.json = json_doc
        self.bin = bytearray(bin_chunk)

    @classmethod
    def load(cls, path):
        data = Path(path).read_bytes()
        magic, version, _length = struct.unpack_from("<4sII", data, 0)
        if magic != b"glTF" or version != 2:
            raise ValueError(f"{path} is not a glTF 2.0 GLB")

        json_doc = None
        bin_chunk = None
        offset = 12
        while offset < len(data):
            chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
            offset += 8
            chunk = data[offset : offset + chunk_length]
            offset += chunk_length
            if chunk_type == JSON_CHUNK:
                json_doc = json.loads(chunk.decode("utf-8"))
            elif chunk_type == BIN_CHUNK:
                bin_chunk = chunk

        if json_doc is None or bin_chunk is None:
            raise ValueError(f"{path} is missing JSON or BIN chunks")

        return cls(json_doc, bin_chunk)

    def save(self, path):
        self.json.setdefault("buffers", [{"byteLength": 0}])
        self.json["buffers"][0]["byteLength"] = len(self.bin)

        json_bytes = pad4(
            json.dumps(self.json, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        bin_bytes = pad4(bytes(self.bin), b"\x00")

        total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
        header = struct.pack("<4sII", b"glTF", 2, total_length)
        json_header = struct.pack("<II", len(json_bytes), JSON_CHUNK)
        bin_header = struct.pack("<II", len(bin_bytes), BIN_CHUNK)

        Path(path).write_bytes(header + json_header + json_bytes + bin_header + bin_bytes)

    def accessor_values(self, accessor_index):
        accessor = self.json["accessors"][accessor_index]
        buffer_view = self.json["bufferViews"][accessor["bufferView"]]
        component_type = accessor["componentType"]
        value_type = accessor["type"]
        count = accessor["count"]
        item_count = TYPE_COUNTS[value_type]
        component_size = COMPONENT_SIZES[component_type]
        stride = buffer_view.get("byteStride", item_count * component_size)
        start = buffer_view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        fmt = "<" + COMPONENT_FORMATS[component_type] * item_count

        values = []
        for index in range(count):
            offset = start + index * stride
            values.append(struct.unpack_from(fmt, self.bin, offset))
        return values

    def append_accessor(self, values, value_type, component_type=5126):
        item_count = TYPE_COUNTS[value_type]
        fmt = "<" + COMPONENT_FORMATS[component_type] * item_count

        while len(self.bin) % 4:
            self.bin.append(0)

        byte_offset = len(self.bin)
        for value in values:
            if item_count == 1:
                packed_value = (value[0] if isinstance(value, (tuple, list)) else value,)
            else:
                packed_value = tuple(value)
            self.bin.extend(struct.pack(fmt, *packed_value))

        byte_length = len(self.bin) - byte_offset
        buffer_view_index = len(self.json.setdefault("bufferViews", []))
        self.json["bufferViews"].append(
            {"buffer": 0, "byteOffset": byte_offset, "byteLength": byte_length}
        )

        accessor = {
            "bufferView": buffer_view_index,
            "byteOffset": 0,
            "componentType": component_type,
            "count": len(values),
            "type": value_type,
        }

        if values:
            columns = list(zip(*[tuple(v) if isinstance(v, (tuple, list)) else (v,) for v in values]))
            accessor["min"] = [min(column) for column in columns]
            accessor["max"] = [max(column) for column in columns]

        accessor_index = len(self.json.setdefault("accessors", []))
        self.json["accessors"].append(accessor)
        return accessor_index


def find_node_index(json_doc, name):
    for index, node in enumerate(json_doc.get("nodes", [])):
        if node.get("name") == name:
            return index
    raise ValueError(f"Node not found: {name}")


def find_animation(json_doc, name):
    for animation in json_doc.get("animations", []):
        if animation.get("name") == name:
            return animation
    raise ValueError(f"Animation not found: {name}")
