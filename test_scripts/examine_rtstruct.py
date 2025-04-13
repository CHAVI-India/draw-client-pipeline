import pydicom

def find_referenced_series_uid(dataset):
    found_uid = None
    def callback(ds, elem):
        nonlocal found_uid
        if elem.tag == (0x0020, 0x000E):  # Series Instance UID tag
            print(f'Found UID at {elem.tag}: {elem.value}')
            found_uid = elem.value
    dataset.walk(callback)
    return found_uid

# Read the DICOM file
ds = pydicom.dcmread('/mnt/share/draw-client-pipeline/folders/folder_deidentified_rtstruct/2025.4.2.21.9.22.18488.803506.1.0.1_rtstruct.dcm')

print("Examining Referenced Frame of Reference Sequence:")
if hasattr(ds, 'ReferencedFrameOfReferenceSequence'):
    for ref_for in ds.ReferencedFrameOfReferenceSequence:
        print("\nFrame of Reference UID:", ref_for.FrameOfReferenceUID)
        if hasattr(ref_for, 'RTReferencedStudySequence'):
            for ref_study in ref_for.RTReferencedStudySequence:
                print("  Referenced SOP Class UID:", ref_study.ReferencedSOPClassUID)
                if hasattr(ref_study, 'RTReferencedSeriesSequence'):
                    for ref_series in ref_study.RTReferencedSeriesSequence:
                        print("  Referenced Series Instance UID:", ref_series.SeriesInstanceUID)
else:
    print("No Referenced Frame of Reference Sequence found")

print("\nAll UIDs in file:")
def print_uids(dataset, indent=""):
    for elem in dataset:
        if hasattr(elem, 'value'):
            if isinstance(elem.value, str) and '.' in elem.value:
                print(f"{indent}{elem.tag}: {elem.name} = {elem.value}")
        if elem.VR == "SQ":
            for item in elem.value:
                print_uids(item, indent + "  ")

print_uids(ds)

# Find the Referenced Series Instance UID
ref_series_uid = find_referenced_series_uid(ds)
print(f'Referenced Series Instance UID: {ref_series_uid}')

# Print some additional information about the structure
print("\nDICOM Structure:")
for elem in ds:
    if elem.tag.group == 0x3006:  # RT Structure Set specific tags
        print(f"{elem.tag}: {elem.name}") 