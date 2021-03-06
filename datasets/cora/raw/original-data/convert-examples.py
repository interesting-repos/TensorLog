import sys
import tensorlog
import re

def cvtExamples(fIn,fOut,prefix):
    fp = open(fOut,'w')
    regex = re.compile('samebib\((\w+),(\w+)')
    for line in open(fIn):
        parts = line.strip().split("\t")
        m = regex.search(parts[0])
        if m:
            queryX = m.group(1)
            pos = []
            for ans in parts[1:]:
                if ans[0]=='+':
                    m = regex.search(ans[1:])
                    pos.append(m.group(2))
            if pos:
                for p in pos: fp.write('%s_samebib\t%s\t%s\n' % (prefix,queryX,p))
    print 'produced',fOut

if __name__ == "__main__":
    for pref in ['train','test']:
        cvtExamples('%s.examples' % pref, 'cora-%s.cfacts' % (pref), pref)
