"coco unit tests"

# pylint:disable=all

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

COCO_EXECUTABLE = Path(
    os.environ.get("COFE_STAND", r"C:\Program Files\COCO\x64\COFEStand.exe")
)
FLOWSHEETS = sorted(Path(__file__).parent.glob("*.fsd"))


def _fresh_flowsheet(source: Path, destination: Path) -> None:
    """Copy a flowsheet while removing COFE's persisted diagnostic log."""
    with zipfile.ZipFile(source) as archive:
        xml = ElementTree.fromstring(archive.read("Flowsheet.xml"))
        for line in list(xml.iter("line")):
            if line.attrib.get("color") == "FF0000":
                parent = next(parent for parent in xml.iter() if line in list(parent))
                parent.remove(line)
        content = ElementTree.tostring(xml, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output:
            for item in archive.infolist():
                output.writestr(
                    item,
                    content if item.filename == "Flowsheet.xml" else archive.read(item),
                )


@pytest.mark.parametrize("flowsheet", FLOWSHEETS, ids=lambda path: path.name)
def test_flowsheet_solves_in_coco(tmp_path, flowsheet):
    if not COCO_EXECUTABLE.is_file():
        pytest.skip("COFEStand.exe is not installed")

    target = tmp_path / flowsheet.name
    _fresh_flowsheet(flowsheet, target)
    result = subprocess.run(
        [str(COCO_EXECUTABLE), str(target)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "SOLVE: OK" in result.stdout

    with zipfile.ZipFile(target) as archive:
        xml = ElementTree.fromstring(archive.read("Flowsheet.xml"))
    errors = [
        (line.text or "").strip()
        for line in xml.iter("line")
        if line.attrib.get("color") == "FF0000"
    ]
    assert errors == [], "\n".join(errors)
