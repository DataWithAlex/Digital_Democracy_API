# utils.py

# Define the list of categories with their names and IDs
categories = [
    {"name": "Animals", "id": "668329ae71bf22a23a6ac94b"},
    {"name": "International Relations", "id": "663299c73b94826974bd24da"},
    {"name": "National Security", "id": "6632997a194f0d20b0d24108"},
    {"name": "Civil Rights", "id": "663298e4562bd3696c89b3ea"},
    {"name": "Arts", "id": "660ede71e88a45fcd08e2e39"},
    {"name": "Energy", "id": "660ed44984debef46e8d5c5d"},
    {"name": "Military and Veterans", "id": "65ce5778dae6450ac15a2d2f"},
    {"name": "Priority Bill", "id": "65ba9dbe9768a6290a95c945"},
    {"name": "Media", "id": "65b550562534316ee17131c0"},
    {"name": "LGBT", "id": "655288ef928edb128306753e"},
    {"name": "Public Records", "id": "655288ef928edb128306753d"},
    {"name": "Social Welfare", "id": "655288ef928edb12830673e2"},
    {"name": "Technology", "id": "655288ef928edb128306743e"},
    {"name": "Government", "id": "655288ef928edb12830673e1"},
    {"name": "Business", "id": "655288ef928edb128306746b"},
    {"name": "Employment", "id": "655288ef928edb1283067425"},
    {"name": "Public Safety", "id": "655288ef928edb1283067442"},
    {"name": "Drugs", "id": "655288ef928edb128306745e"},
    {"name": "Immigration", "id": "655288ef928edb12830673e5"},
    {"name": "Transportation", "id": "655288ef928edb1283067415"},
    {"name": "Criminal Justice", "id": "655288ef928edb12830673dc"},
    {"name": "Elections", "id": "655288ef928edb12830673e0"},
    {"name": "Culture", "id": "655288ef928edb1283067436"},
    {"name": "Sports", "id": "655288ef928edb12830673df"},
    {"name": "Marriage", "id": "655288ef928edb128306742d"},
    {"name": "Housing", "id": "655288ef928edb128306743d"},
    {"name": "Education", "id": "655288ef928edb12830673e4"},
    {"name": "Medical", "id": "655288ef928edb12830673e9"},
    {"name": "State Parks", "id": "655288ef928edb128306745d"},
    {"name": "Guns", "id": "655288ef928edb128306741f"},
    {"name": "Disney", "id": "655288ef928edb128306742c"},
    {"name": "Natural Disasters", "id": "655288ef928edb1283067435"},
    {"name": "Environment", "id": "655288ef928edb128306741b"},
    {"name": "Taxes", "id": "655288ef928edb128306745c"}
]

# Create a dictionary for quick lookup
category_dict = {category["name"].lower(): category["id"] for category in categories}

def get_category_ids(category_names):
    """
    Given a list of category names, return the corresponding category IDs.
    """
    category_ids = []
    for name in category_names:
        # Convert name to lowercase to match the dictionary keys
        category_id = category_dict.get(name.lower())
        if category_id:
            category_ids.append(category_id)
        else:
            print(f"Warning: Category '{name}' not found in predefined categories.")
    return category_ids