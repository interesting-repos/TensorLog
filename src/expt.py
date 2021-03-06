# (C) William W. Cohen and Carnegie Mellon University, 2016

#
# support for running experiments
#

import sys
import time
import logging
import collections

import tensorlog
import dataset
import matrixdb
import tensorlog
import declare
import learn
import mutil
import config

conf = config.Config()

class Expt(object):

    def __init__(self,configDict):
        self.config = configDict

    def run(self):
        return self._run(**self.config)

    #TODO targetPred->targetMode
    def _run(self,
             prog=None, trainData=None, testData=None, targetMode=None, 
             savedTestPredictions=None, savedTestExamples=None, savedTrainExamples=None, savedModel=None,
             learner=None):

        """ Run an experiment.  

        The stages are
        - if targetMode is specified, extract just the examples from that mode from trainData and testData
        - evaluate the untrained program on the train and test data and print results
        - train on the trainData
        - if savedModel is given, write the learned database, including the trained parameters,
          to that directory.
        - if savedTestPredictions is given, write the test-data predictions in ProPPR format
        - if savedTestExamples (savedTrainExamples) is given, save the training/test examples in ProPPR format
        """

        if targetMode: 
            targetMode = declare.asMode(targetMode)
            trainData = trainData.extractMode(targetMode)
            testData = testData.extractMode(targetMode)

        if not learner: learner = learn.FixedRateGDLearner(prog)

        TP0 = Expt.timeAction(
            'running untrained theory on train data',
            lambda:learner.datasetPredict(trainData))
        UP0 = Expt.timeAction(
            'running untrained theory on test data',
            lambda:learner.datasetPredict(testData))
        Expt.printStats('untrained theory','train',trainData,TP0)
        Expt.printStats('untrained theory','test',testData,UP0)

        Expt.timeAction('training', lambda:learner.train(trainData))

        TP1 = Expt.timeAction(
            'running trained theory on train data',
            lambda:learner.datasetPredict(trainData))
        UP1 = Expt.timeAction(
            'running trained theory on test data',
            lambda:learner.datasetPredict(testData))

        Expt.printStats('..trained theory','train',trainData,TP1)
        testAcc,testXent = Expt.printStats('..trained theory','test',testData,UP1)

        if savedModel:
            Expt.timeAction('saving trained model', lambda:prog.db.serialize(savedModel))

        if savedTestPredictions:
            #todo move this logic to a dataset subroutine
            open(savedTestPredictions,"w").close() # wipe file first
            def doit():
                qid=0
                for mode in testData.modesToLearn():
                    qid+=Expt.predictionAsProPPRSolutions(savedTestPredictions,mode.functor,prog.db,UP1.getX(mode),UP1.getY(mode),True,qid) 
            Expt.timeAction('saving test predictions', doit)

        if savedTestExamples:
            Expt.timeAction('saving test examples', 
                            lambda:testData.saveProPPRExamples(savedTestExamples,prog.db))

        if savedTrainExamples:
            Expt.timeAction('saving train examples', 
                            lambda:trainData.saveProPPRExamples(savedTrainExamples,prog.db))
                
        if savedTestPredictions and savedTestExamples:
            print 'ready for commands like: proppr eval %s %s --metric auc --defaultNeg' \
                % (savedTestExamples,savedTestPredictions)

        return testAcc,testXent


    @staticmethod
    def predictionAsProPPRSolutions(fileName,theoryPred,db,X,P,append=False,start=0):
        """Print X and P in the ProPPR solutions.txt format."""
        fp = open(fileName,'a' if append else 'w')
        dx = db.matrixAsSymbolDict(X)
        dp = db.matrixAsSymbolDict(P)
        n=max(dx.keys())
        for i in range(n):
            dix = dx[i]
            dip = dp[i]
            assert len(dix.keys())==1,'X %s row %d is not onehot: %r' % (theoryPred,i,dix)
            x = dix.keys()[0]    
            fp.write('# proved %d\t%s(%s,X1).\t999 msec\n' % (i+1+start,theoryPred,x))
            scoresdPs = reversed(sorted([(py,y) for (y,py) in dip.items()]))
            for (r,(py,y)) in enumerate(scoresdPs):
                fp.write('%d\t%.18f\t%s(%s,%s).\n' % (r+1,py,theoryPred,x,y))
        return n

    @staticmethod
    def timeAction(msg, act):
        """Do an action encoded as a callable function, return the result,
        while printing the elapsed time to stdout."""
        print msg,'...'
        start = time.time()
        result = act()
        print msg,'... done in %.3f sec' % (time.time()-start)
        return result

    @staticmethod
    def printStats(modelMsg,testSet,goldData,predictedData):
        """Print accuracy and crossEntropy for some named model on a named eval set."""
        acc = learn.Learner.datasetAccuracy(goldData,predictedData)
        xent = learn.Learner.datasetCrossEntropy(goldData,predictedData,perExample=True)
        print 'eval',modelMsg,'on',testSet,': acc',acc,'xent/ex',xent
        return (acc,xent)

# a sample main

if __name__=="__main__":

    try: 
        optdict,args = tensorlog.parseCommandLine(sys.argv[1:])
        optdict['prog'].setWeights(optdict['prog'].db.ones())
        params = {'prog':optdict['prog'],
                  'trainData':optdict['trainData'],
                  'testData':optdict['testData'],
                  'savedModel':'expt-model.db'}
        Expt(params).run()
        print 'saved in expt-model.db'

    except Exception:

        def usage():
            print 'usage: python expt.py --prog a --db b --trainData c --testData d'
            print 'usage: python expt.py [textcattoy|matchtoy]'

        if len(sys.argv)<2:
            usage()
        elif sys.argv[1]=='textcattoy':
            db = matrixdb.MatrixDB.uncache('tlog-cache/textcat.db','test/textcattoy.cfacts')
            trainData = dataset.Dataset.uncacheMatrix('tlog-cache/train.dset',db,'predict/io','train')
            testData = dataset.Dataset.uncacheMatrix('tlog-cache/test.dset',db,'predict/io','test')
            prog = tensorlog.ProPPRProgram.load(["test/textcat.ppr"],db=db)
            initWeights = \
                (prog.db.matrixPreimage(declare.asMode("posPair(o,i)")) + \
                     prog.db.matrixPreimage(declare.asMode("negPair(o,i)"))) * 0.5
        elif sys.argv[1]=='matchtoy':
            db = matrixdb.MatrixDB.loadFile('test/matchtoy.cfacts')
            trainData = dataset.Dataset.loadExamples(db,'test/matchtoy-train.exam')
            testData = trainData
            prog = tensorlog.ProPPRProgram.load(["test/matchtoy.ppr"],db=db)
            initWeights = prog.db.ones()
        else:
            usage()

        prog.setWeights(initWeights)

        myLearner = learn.FixedRateGDLearner(prog)
        #myLearner = learn.FixedRateSGDLearner(prog)

        params = {'prog':prog,
                  'trainData':trainData, 'testData':testData,
                  'savedModel':'toy-trained.db',
                  'learner':myLearner
                  }
        Expt(params).run()
