#!/usr/bin/env python3
"""Generate index.html (fetch data, timeline + session filter)."""
import json, os

def main():
    data = json.load(open('data/conversations.json'))
    total = len(data['conversations'])
    dates = [c['created_at'] for c in data['conversations'] if c.get('created_at')]
    span = dates[-1][:7] + ' ~ ' + dates[0][:7] if len(dates)>1 else ''
    chatgpt = sum(1 for c in data['conversations'] if c['model'] == 'ChatGPT')
    gemini = total - chatgpt

    html = open(os.path.join(os.path.dirname(__file__), '_template.html')).read()
    html = html.replace('{TOTAL}', str(total))
    html = html.replace('{SPAN}', span)
    html = html.replace('{CHATGPT}', str(chatgpt))
    html = html.replace('{GEMINI}', str(gemini))

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('✓ index.html (' + str(os.path.getsize('index.html')//1024) + ' KB)')

if __name__ == '__main__':
    main()
