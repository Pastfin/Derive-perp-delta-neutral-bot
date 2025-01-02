
def extract_data() -> dict:
    with open('./creds.txt', 'r', encoding='utf-8') as file:
        raw_data = file.read()
    
    result = []
    for line in raw_data.strip().split('\n'):
        splitted_data = line.split(':')
        
        if len(splitted_data) < 7:
            raise ValueError(f"Invalid data format in line: {line}")
        
        proxy = {
            'http': f'http://{splitted_data[5]}:{splitted_data[6]}@{splitted_data[3]}:{splitted_data[4]}',
            'https': f'http://{splitted_data[5]}:{splitted_data[6]}@{splitted_data[3]}:{splitted_data[4]}'
        }
        
        result.append({
            'derive_wallet': splitted_data[0],
            'subacc_id': int(splitted_data[1]),
            'session_pk': splitted_data[2],
            'proxy': proxy
        })
    
    return result
