def select_by_key(keyname, options):
    def selecting(input_dict):
        if not keyname in input_dict:
            return None
        pick = input_dict[keyname]
        if not pick in options:
            if "default" in options:
                pick = "default"
            else:
                return None
        if (pick in options):
            return options[pick](input_dict)
        else:
            return None
    return selecting
