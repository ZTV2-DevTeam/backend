"""
Sample XLSX data generator for testing the configuration wizard.
This script creates sample XLSX files that can be used to test the upload functionality.
"""

import pandas as pd
import os

def create_sample_xlsx_files():
    """Create sample XLSX files for testing."""
    
    # Create templates directory if it doesn't exist
    templates_dir = "sample_templates"
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # Classes template
    classes_data = [
        {'start_year': 2024, 'section': 'F', 'school_year': '2024/2025', 'class_teachers': 'Nagy János'},
        {'start_year': 2023, 'section': 'F', 'school_year': '2024/2025', 'class_teachers': 'Kis Petra'},
        {'start_year': 2022, 'section': 'F', 'school_year': '2024/2025', 'class_teachers': 'Szabó Mihály'},
        {'start_year': 2023, 'section': 'A', 'school_year': '2024/2025', 'class_teachers': 'Tóth Anna'},
        {'start_year': 2022, 'section': 'B', 'school_year': '2024/2025', 'class_teachers': 'Varga Béla'},
    ]
    df_classes = pd.DataFrame(classes_data)
    df_classes.to_excel(f"{templates_dir}/classes_sample.xlsx", index=False)
    
    # Stabs template
    stabs_data = [
        {'name': 'A stáb', 'description': 'Első műszak média stáb', 'type': 'media'},
        {'name': 'B stáb', 'description': 'Második műszak média stáb', 'type': 'media'},
        {'name': 'C stáb',             'description': 'Diákok adatai és osztályok hozzárendelése - felhasználónév, név, email és osztály kötelező. Rádiós stáb: A1, A2, B3, B4', 'type': 'media'},
        {'name': 'Karbantartó stáb', 'description': 'Eszközök karbantartása és javítása', 'type': 'maintenance'},
        {'name': 'Vágó stáb', 'description': 'Post-production és vágás', 'type': 'editing'},
    ]
    df_stabs = pd.DataFrame(stabs_data)
    df_stabs.to_excel(f"{templates_dir}/stabs_sample.xlsx", index=False)
    
    # Teachers template
    teachers_data = [
        {
            'username': 'nagy.janos',
            'first_name': 'János',
            'last_name': 'Nagy',
            'email': 'nagy.janos@iskola.hu',
            'phone': '+36301234567',
            'admin_type': 'teacher',
            'special_role': 'none',
            'assigned_classes': '2024F,2023A'
        },
        {
            'username': 'kis.petra',
            'first_name': 'Petra',
            'last_name': 'Kis',
            'email': 'kis.petra@iskola.hu',
            'phone': '+36309876543',
            'admin_type': 'teacher',
            'special_role': 'none',
            'assigned_classes': '2023F'
        },
        {
            'username': 'szabo.mihaly',
            'first_name': 'Mihály',
            'last_name': 'Szabó',
            'email': 'szabo.mihaly@iskola.hu',
            'phone': '+36307654321',
            'admin_type': 'system_admin',
            'special_role': 'none',
            'assigned_classes': ''
        },
        {
            'username': 'toth.anna',
            'first_name': 'Anna',
            'last_name': 'Tóth',
            'email': 'toth.anna@iskola.hu',
            'phone': '+36305551234',
            'admin_type': 'teacher',
            'special_role': 'production_leader',
            'assigned_classes': '2022F,2022A'
        }
    ]
    df_teachers = pd.DataFrame(teachers_data)
    df_teachers.to_excel(f"{templates_dir}/teachers_sample.xlsx", index=False)
    
    # Students template
    students_data = [
        {
            'username': 'toth.zoltan',
            'first_name': 'Zoltán',
            'last_name': 'Tóth',
            'email': 'toth.zoltan@student.hu',
            'phone': '+36301111111',
            'class_start_year': 2024,
            'class_section': 'F',
            'stab': 'A stáb',
            'radio_stab': ''
        },
        {
            'username': 'kovacs.eszter',
            'first_name': 'Eszter',
            'last_name': 'Kovács',
            'email': 'kovacs.eszter@student.hu',
            'phone': '+36302222222',
            'class_start_year': 2024,
            'class_section': 'F',
            'stab': 'B stáb',
            'radio_stab': ''
        },
        {
            'username': 'horvath.david',
            'first_name': 'Dávid',
            'last_name': 'Horváth',
            'email': 'horvath.david@student.hu',
            'phone': '',
            'class_start_year': 2023,
            'class_section': 'F',
            'stab': 'A stáb',
            'radio_stab': 'A1'
        },
        {
            'username': 'varga.boglarka',
            'first_name': 'Boglárka',
            'last_name': 'Varga',
            'email': 'varga.boglarka@student.hu',
            'phone': '+36304444444',
            'class_start_year': 2023,
            'class_section': 'F',
            'stab': 'B stáb',
            'radio_stab': 'B3'
        },
        {
            'username': 'simon.petra',
            'first_name': 'Petra',
            'last_name': 'Simon',
            'email': 'simon.petra@student.hu',
            'phone': '+36305555555',
            'class_start_year': 2022,
            'class_section': 'F',
            'stab': 'C stáb',
            'radio_stab': ''
        },
        {
            'username': 'feher.adam',
            'first_name': 'Ádám',
            'last_name': 'Fehér',
            'email': 'feher.adam@student.hu',
            'phone': '',
            'class_start_year': 2023,
            'class_section': 'A',
            'stab': 'A stáb',
            'radio_stab': ''
        },
        {
            'username': 'molnar.lilla',
            'first_name': 'Lilla',
            'last_name': 'Molnár',
            'email': 'molnar.lilla@student.hu',
            'phone': '+36307777777',
            'class_start_year': 2022,
            'class_section': 'B',
            'stab': 'B stáb',
            'radio_stab': ''
        }
    ]
    df_students = pd.DataFrame(students_data)
    df_students.to_excel(f"{templates_dir}/students_sample.xlsx", index=False)
    
    print(f"Sample XLSX files created in {templates_dir}/ directory:")
    print("- classes_sample.xlsx")
    print("- stabs_sample.xlsx") 
    print("- teachers_sample.xlsx")
    print("- students_sample.xlsx")

if __name__ == "__main__":
    create_sample_xlsx_files()
