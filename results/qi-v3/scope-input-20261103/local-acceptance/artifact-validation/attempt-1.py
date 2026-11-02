def normalize(value):
 if not isinstance(value, str): raise TypeError('string required')
 return value.strip().lower()
