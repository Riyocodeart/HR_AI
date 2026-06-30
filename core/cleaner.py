import json

class DataCleaner:
    
    PENALTIES = {
    "missing_name": 20,
    "missing_role": 15,
    "missing_location": 5,
    "missing_skills": 25,
    "missing_company": 5,
    "missing_education": 10,
    "invalid_email":10,
    "invalid_experience": 20,
    }
    ACCEPTED_SCORE = 80
    REVIEW_SCORE = 50

    location_map = {

    # Bengaluru
    "Bangalore": "Bengaluru, Karnataka",
    "Bangalore, Karnataka": "Bengaluru, Karnataka",
    "Bengaluru": "Bengaluru, Karnataka",

    # Mumbai
    "Bombay": "Mumbai, Maharashtra",
    "Mumbai": "Mumbai, Maharashtra",
    "Mumbai, India": "Mumbai, Maharashtra",

    # Delhi
    "Delhi": "Delhi, Delhi",
    "New Delhi": "Delhi, Delhi",

    # Gurugram
    "Gurgaon": "Gurugram, Haryana",
    "Gurgaon, Haryana": "Gurugram, Haryana",

    # Hyderabad
    "Hyderabad": "Hyderabad, Telangana",

    # Chennai
    "Madras": "Chennai, Tamil Nadu",
    "Chennai": "Chennai, Tamil Nadu",

    # Kolkata
    "Calcutta": "Kolkata, West Bengal",
    "Kolkata": "Kolkata, West Bengal",

    # Pune
    "Pune": "Pune, Maharashtra",

    # Ahmedabad
    "Ahmedabad": "Ahmedabad, Gujarat",

    # Jaipur
    "Jaipur": "Jaipur, Rajasthan",

    # Noida
    "Noida": "Noida, Uttar Pradesh",

    # Chandigarh
    "Chandigarh": "Chandigarh, Chandigarh",

    # Kochi
    "Cochin": "Kochi, Kerala",
    "Kochi": "Kochi, Kerala",

    # Trivandrum
    "Trivandrum": "Thiruvananthapuram, Kerala",

    # Vizag
    "Vizag": "Visakhapatnam, Andhra Pradesh",

    # Indore
    "Indore": "Indore, Madhya Pradesh",

    # Coimbatore
    "Coimbatore": "Coimbatore, Tamil Nadu",

    # Bhubaneswar
    "Bhubaneswar": "Bhubaneswar, Odisha",

    # International
    "New York": "New York",
    "San Francisco": "San Francisco",
    "Seattle": "Seattle",
    "Austin": "Austin",
    "Toronto": "Toronto",
    "London": "London",
    "Berlin": "Berlin",
    "Singapore": "Singapore",
    "Sydney": "Sydney",
    "Dubai": "Dubai"
}
        

    def clean_jsonl(self, input_file, output_file, rejected_file=None):
        """
        Blueprint (datacleaning.md, Step 5/6): Accepted + Needs Review candidates
        go to `output_file` (validated_candidates.json) and feed the scoring
        engine. Rejected candidates go to a SEPARATE `rejected_file`
        (rejected_candidates.json) for audit/logging only, and must never reach
        the scorer. Previously every row was written to `output_file`
        regardless of status, so Rejected rows ended up in scoring too.
        """
        if rejected_file is None:
            rejected_file = output_file.rsplit(".", 1)[0] + ".rejected.jsonl" \
                if "." in output_file else output_file + ".rejected"

        with open(input_file, "r", encoding="utf-8") as infile, \
             open(output_file, "w", encoding="utf-8") as valid_out, \
             open(rejected_file, "w", encoding="utf-8") as reject_out:

            for line in infile:
                candidate = json.loads(line)
                candidate = self.clean_candidate(candidate)

                if candidate["status"] == "Rejected":
                    reject_out.write(json.dumps(candidate, ensure_ascii=False) + "\n")
                else:
                    # Accepted or Needs Review -> validated output, scoring-eligible
                    valid_out.write(json.dumps(candidate, ensure_ascii=False) + "\n")

    def clean_candidate(self, candidate):
        candidate["quality_score"] = 100
        candidate["warnings"] = []
        
        candidate = self.standardize_names(candidate)
        candidate = self.standardize_roles(candidate)
        candidate = self.standardize_locations(candidate)
        candidate = self.standardize_skills(candidate)
        candidate = self.standardize_companies(candidate)
        candidate = self.standardize_education(candidate)
        candidate = self.validate_email(candidate)
        candidate = self.standardize_experience(candidate)

        candidate = self.validate_names(candidate)
        candidate = self.validate_roles(candidate)
        candidate = self.validate_locations(candidate)
        candidate = self.validate_skills(candidate)
        candidate = self.validate_companies(candidate)
        candidate = self.validate_education(candidate)
        candidate = self.validate_experience(candidate)

        candidate=self.classify_candidate(candidate)
        candidate["warnings"] = "; ".join(candidate["warnings"])    
        return candidate
        
    def standardize_names(self, candidate):

        candidate["profile"]["anonymized_name"] = (
            str(candidate.get("profile", {}).get("anonymized_name", ""))
            .strip()
            .title()
        )
        return candidate

    def standardize_roles(self, candidate):

        candidate["profile"]["current_title"] = (
            str(candidate.get("profile", {}).get("current_title", ""))
            .strip()
            .title()
        )
        return candidate

    def standardize_locations(self, candidate):

        location = (
              str(candidate.get("profile", {}).get("location", ""))
            .strip()
            .title()
        )
        candidate["profile"]["location"] = self.location_map.get(location, location)

        return candidate
    
    def standardize_skills(self, candidate):

        for skill in candidate.get("skills", []):
            skill["name"] = skill.get("name", "").strip().lower()

        return candidate
    
    def standardize_companies(self, candidate):

        candidate["profile"]["current_company"] = (
            str(candidate.get("profile", {}).get("current_company", ""))
            .strip()
            .title()
        )
        return candidate

    def standardize_education(self, candidate):

        for edu in candidate.get("education", []):
            edu["institution"] = edu.get("institution", "").strip().title()
            edu["degree"] = edu.get("degree", "").strip().title()

        return candidate

    
    def standardize_experience(self, candidate):

        try:
            candidate["profile"]["years_of_experience"] = float(
                candidate.get("profile", {}).get("years_of_experience", 0)
                )
            
        except (ValueError, TypeError):
            candidate["profile"]["years_of_experience"] = 0

        return candidate
    
    def validate_names(self, candidate):

        if not candidate.get("profile", {}).get("anonymized_name", "").strip():

            candidate["quality_score"] -= self.PENALTIES["missing_name"]

            candidate["warnings"].append("Missing Name")

        return candidate

    def validate_roles(self, candidate):

        if not candidate.get("profile", {}).get("current_title", "").strip():

            candidate["quality_score"] -= self.PENALTIES["missing_role"]

            candidate["warnings"].append("Missing Role")

        return candidate

    def validate_locations(self, candidate):

        if not candidate.get("profile", {}).get("location", "").strip():

            candidate["quality_score"] -= self.PENALTIES["missing_location"]
            
            candidate["warnings"].append("Missing Location")

        return candidate
        
    def validate_skills(self, candidate):

        if not candidate.get("skills"):
            
            candidate["quality_score"] -= self.PENALTIES["missing_skills"]

            candidate["warnings"].append("Missing Skills")

        return candidate
        
    def validate_companies(self, candidate):

        if not candidate.get("profile", {}).get("current_company", "").strip():

            candidate["quality_score"] -= self.PENALTIES["missing_company"]

            candidate["warnings"].append("Missing Company")

        return candidate
    
    def validate_email(self, candidate):

        verified = candidate.get("redrob_signals", {}).get("verified_email", False)

        if not verified:
            candidate["quality_score"] -= self.PENALTIES["invalid_email"]
            candidate["warnings"].append("Email Not Verified")

        return candidate

    def validate_education(self, candidate):

        if not candidate.get("education"):

            candidate["quality_score"] -= self.PENALTIES["missing_education"]

            candidate["warnings"].append("Missing Education")

        return candidate

    
    def validate_experience(self, candidate):

        exp = candidate.get("profile", {}).get("years_of_experience", 0)

        if exp < 0 or exp > 50:

            candidate["quality_score"] -= self.PENALTIES["invalid_experience"]

            candidate["warnings"].append("Invalid Experience")

        return candidate

    def classify_candidate(self, candidate):

        candidate["status"] = "Accepted"

        if candidate["quality_score"] < self.ACCEPTED_SCORE:
            candidate["status"] = "Needs Review"

        if candidate["quality_score"] < self.REVIEW_SCORE:
            candidate["status"] = "Rejected"

        return candidate