import itertools
import random
import pytest
from app.algorithms import maximum_weight, greedy, benchmark
from app import models as m
from app.services import score

def value(matrix,pairs):
    return sum(matrix[i][j] for i,j in pairs)

def test_counterexample():
    matrix=[[9,8],[8,1]]
    assert value(matrix,greedy(matrix))==10
    assert value(matrix,maximum_weight(matrix))==16

@pytest.mark.parametrize('matrix',[[],[[]],[[None,None]],[[0,-1]],[[5],[4]],[[2,2],[2,2]]])
def test_edge_cases_deterministic(matrix):
    chosen=maximum_weight(matrix)
    assert chosen==maximum_weight(matrix)
    assert len({i for i,j in chosen})==len(chosen)
    assert len({j for i,j in chosen})==len(chosen)
    assert all(matrix[i][j] is not None and matrix[i][j]>0 for i,j in chosen)

def test_against_exhaustive_oracle():
    rng=random.Random(42)
    for _ in range(60):
        n,width=rng.randint(1,4),rng.randint(1,4)
        matrix=[[rng.randint(1,15) if rng.random()>.3 else None for j in range(width)] for i in range(n)]
        best=0
        for assignment in itertools.product(range(-1,width),repeat=n):
            used=[j for j in assignment if j>=0]
            if len(used)!=len(set(used)) or any(j>=0 and matrix[i][j] is None for i,j in enumerate(assignment)):
                continue
            best=max(best,sum(matrix[i][j] for i,j in enumerate(assignment) if j>=0))
        assert value(matrix,maximum_weight(matrix))==best

def test_fifty_benchmarks():
    result=benchmark()
    assert result['scenario_count']==50
    for scenario in result['scenarios']:
        assert scenario['optimized']['total_utility']>=scenario['greedy']['total_utility']-.0001
        assert scenario['optimized']['invalid_assignments']==0
    second=benchmark()
    for a,b in zip(result['scenarios'],second['scenarios']):
        assert a['optimized']['total_utility']==b['optimized']['total_utility']

@pytest.mark.parametrize('tags,relevance',[(['python'],35),(['python','loops'],27.5)])
def test_exact_partial_provisional_urgency(tags,relevance):
    doubt=m.DoubtRequest(domain='Python',urgency='Urgent',created_at=0,skills=[m.DoubtSkill(tag=t) for t in tags])
    mentor=m.Student(skills=[m.StudentSkill(domain='Python',tag='python',level=3)])
    result=score(doubt,mentor,3600,3600,None,0,0)
    assert result['skill_relevance']==relevance
    assert result['assessment_evidence']==10
    assert result['confidence']==4
    assert result['reliability']==7.5
    assert result['urgency_multiplier']==1.25
    assert result['utility']==round(result['suitability']*1.25+1,6)
    assessed=score(doubt,mentor,3600,3600,m.AssessmentAttempt(score=80),4,3)
    assert assessed['assessment_evidence']==20
    assert assessed['confidence']==10
    assert assessed['reliability']==15*5/8

def test_wait_bonus_bounded_earlier_slot_better():
    doubt=m.DoubtRequest(domain='Python',urgency='Normal',created_at=0,skills=[m.DoubtSkill(tag='python')])
    mentor=m.Student(skills=[m.StudentSkill(domain='Python',tag='python',level=3)])
    early=score(doubt,mentor,86400,86400,None,0,0)
    late=score(doubt,mentor,90000,86400,None,0,0)
    assert early['waiting_bonus']==10
    assert early['availability']>late['availability']
