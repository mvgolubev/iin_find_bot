first_name = "Иван"
last_name = None  # "Петров"
# full_name = f"{first_name} {last_name or ''}"
full_name = f"{first_name}{' '+last_name if last_name else ''}"
print(full_name)
print(len(full_name))
last_name2 = last_name or ''
print(last_name)
print(last_name2)