import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./triage15.db')
OFFER_TTL_SECONDS = int(os.getenv('OFFER_TTL_SECONDS', '300'))
URGENCY = {'Urgent': 1.25, 'Normal': 1.0, 'Flexible': 0.85}
SLOT = 900
DOMAINS = {
    'Python': ['python', 'loops', 'pandas', 'debugging'],
    'JavaScript': ['javascript', 'react', 'async', 'debugging'],
    'SQL': ['sql', 'joins', 'aggregation', 'schema'],
    'CAD': ['cad', 'sketching', 'constraints'],
    'Design': ['design', 'typography', 'layout'],
    'Mathematics': ['algebra', 'calculus', 'probability'],
}
