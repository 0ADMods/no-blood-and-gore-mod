import os
import argparse
import logging
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.INFO)


def clean_xml(file_path):
    """
    Cleans XML by:
    - Removing <prop> elements containing "blood"
    - Deleting empty <props> groups
    - Ensuring <variant> elements have correct frequency values (100 -> 1, missing -> 0)
    - Removing completely empty <variant> elements recursively
    - Removing <group> elements if all its <variant> children are empty
    - Updating <material> from "default.xml" to "no_trans_norm_spec.xml"
    Returns cleaned XML as a string or None if no changes were needed.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        modified = False



        # Find all <prop> elements directly (instead of <props>)
        prop_nodes = root.findall(".//variant/props/prop")

        # Check if any <prop> element contains "blood" in its actor attribute
        has_blood = any("blood" in (prop.get("actor") or "").lower() for prop in prop_nodes)


        # Find all <prop> elements directly (instead of <props>)
        prop_nodes = root.findall(".//props/prop")

        # Check if any <prop> element contains "blood" in its actor attribute
        has_blood = has_blood or any("blood" in (prop.get("actor") or "").lower() for prop in prop_nodes)

        # If no <prop> contains "blood", return False
        if not has_blood:
            return None
        
        # Find all <props> elements inside <variant>
        props_nodes = root.findall(".//props")

        for props in props_nodes:
            props[:] = [prop for prop in props if "blood" not in (prop.get("actor") or "").lower()]
            if not list(props):  # If <props> is empty, remove it
                parent = props.find("..")
                if parent is not None:
                    parent.remove(props)
                    modified = True

        # Ensure <variant> has a frequency, modify as needed
        for variant in root.findall(".//variant"):
            frequency = variant.get("frequency")
            if frequency is None:
                variant.set("frequency", "0")  # Default missing frequency to 0
                modified = True

        def remove_empty_elements(element):
            """
            Recursively removes:
            - <props>, <animations>, <textures> if they are empty
            - <variant> elements that are empty (no children, no file attribute, frequency="0")
            - <group> elements if:
            - It is completely empty
            - It contains only one variant, and that variant is empty or useless
            """
            nonlocal modified
            to_remove = []

            for child in element:
                if child.tag in {"props", "animations", "textures"}:
                    if not list(child):  # No children inside -> remove
                        to_remove.append(child)

                elif child.tag == "variant":
                    remove_empty_elements(child)  # Recurse inside variant
                    if (
                        not list(child)  # No children left
                        and not child.get("file")  # No file attribute
                        and child.get("frequency") == "0"
                    ):
                        to_remove.append(child)

                elif child.tag == "group":
                    remove_empty_elements(child)  # Recurse inside group
                    
                    # Remove the group if it is completely empty
                    if not list(child):
                        to_remove.append(child)
                    # Remove the group if it contains only one variant that is useless
                    elif len(child) == 1 and child[0].tag == "variant":
                        variant = child[0]
                        if (
                            not list(variant)  # No children
                            and not variant.get("file")  # No file attribute
                            and variant.get("frequency") in {"0", "100"}  # Default or unchanged frequency
                        ):
                            to_remove.append(child)

            for item in to_remove:
                element.remove(item)
                modified = True


        # Apply recursive cleaning to the root
        remove_empty_elements(root)

        if modified:
            xml_string = ET.tostring(root, encoding="utf-8").decode("utf-8")
            return f'<?xml version="1.0" encoding="utf-8"?>\n{xml_string}'
        

    except ET.ParseError as e:
        logging.error(f"XML parsing error in {file_path}: {e}")
        return None

    return None  # No modifications needed


def clean_and_copy_xml_files(input_folder, output_folder):
    input_folder = os.path.abspath(input_folder)
    output_folder = os.path.abspath(output_folder)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    logging.info(f"Scanning XML files in {input_folder}")

    for root, _, files in os.walk(input_folder):
        for file in files:
            if not file.endswith(".xml"):  # Only process XML files
                continue

            file_path = os.path.join(root, file)
            cleaned_xml = clean_xml(file_path)

            if cleaned_xml:
                # Preserve folder structure in output directory
                relative_path = os.path.relpath(file_path, input_folder)
                new_file_path = os.path.join(output_folder, relative_path)

                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

                with open(new_file_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_xml)

                logging.info(f"Cleaned and copied: {file_path} → {new_file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean XML by removing unwanted props, fixing variants, and deleting empty groups.")
    parser.add_argument("input_folder", nargs="?", help="Path to the input folder")
    parser.add_argument("output_folder", nargs="?", help="Path to the output folder")

    args = parser.parse_args()

    # Ask user for paths if not provided via command line
    input_folder = args.input_folder or input("Enter the input folder path: ").strip()
    output_folder = args.output_folder or input("Enter the output folder path: ").strip()

    clean_and_copy_xml_files(input_folder, output_folder)

