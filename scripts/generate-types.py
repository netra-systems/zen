from datamodel_code_generator import generate
from pathlib import Path


def main():
    input_file = Path("app/schemas.py")
    output_file = Path("shared/types.ts")
    generate(
        input_file_type='pydantic',
        input_filename=str(input_file),
        output=output_file,
        target_language='typescript',
    )


if __name__ == "__main__":
    main()