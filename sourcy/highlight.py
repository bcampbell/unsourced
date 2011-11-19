from pprint import pprint
import operator
import collections


def walk(text, spans):
    """ yields segments of text split up by the spans """
    # build a sorted list of points where spans start and stop
    transitions = []
    for span in spans:
        transitions.append(('+',span[0],span[2]))
        transitions.append(('-',span[1],span[2]))
    transitions = sorted(transitions, key=operator.itemgetter(1))

    pos = 0
    active = collections.defaultdict(int)
    for t in transitions:
        if pos != t[1]:
            yield((text[pos:t[1]],[a for a in active if active[a]>0]))
        if t[0] == '+':
            active[t[2]] += 1
        if t[0] == '-':
            active[t[2]] -= 1
        pos = t[1]

    if pos != len(text):
        yield((text[pos:],[]))


def html_highlight(text,spans):
    out = u''
    for segment,classes in walk(text, spans):
        if classes:
            out += u'<span class="hilite %s">%s</span>' % (u' '.join(classes),segment)
        else:
            out += segment
    return out


def remove_contained_spans(spans):
    out = []
    for i1,s1 in enumerate(spans):
        contained = False

        for i2,s2 in enumerate(spans):
            if i1==i2:
                continue
            if s1[0]>=s2[0] and s1[1]<=s2[1]:
                contained = True
                break
        if not contained:
            out.append(s1)
    return out

