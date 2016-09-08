import sys

import expt
import declare
import tensorlog
import learn
import plearn
import funs


def setup(optdict, settings):
    # prog is shortcut to the output optdict, for convenience.
    prog = optdict['prog']

    # the weight vector is sparse - just the constants in the unary predicate rule
    prog.setRuleWeights(prog.db.vector(declare.asMode("rule(i)")))
    
    # set the max recursion depth
    prog.maxDepth = settings['maxDepth']
    
    # be verbose
    # funs.conf.trace = True

    # use a non-default learner, overriding the tracing function,
    # number of epochs, and regularizer
    learner = plearn.ParallelFixedRateGDLearner(
        prog,epochs=settings['epochs'],parallel=settings['para'],regularizer=learn.L2Regularizer())

    #learner = learn.FixedRateGDLearner(
    #    prog,epochs=epochs,regularizer=learn.L2Regularizer())

    #learner = learn.FixedRateSGDLearner(
    #    prog,epochs=epochs,regularizer=learn.L2Regularizer())

    #    learner = plearn.ParallelAdaGradLearner(
    #        prog,epochs=epochs,parallel=40,regularizer=learn.L2Regularizer())
    return learner



if __name__=="__main__":
    #usage: [dataset] [epochs] [maxDepth] [threads]
    
    #get the command-line options for this experiment
    settings = {}
    settings['dataset'] = 'yago2-sample' if len(sys.argv)<=1 else sys.argv[1]
    settings['epochs'] = 30 if len(sys.argv)<=2 else int(sys.argv[2])
    settings['maxDepth'] = 1 if len(sys.argv)<=3 else int(sys.argv[3])
    settings['para'] = 30 if len(sys.argv)<=4 else int(sys.argv[4])

    # first run eval set on untrained model:

    optdict,args = tensorlog.parseCommandLine([
        '--logging', 'debug', # was: 'warn'
        '--db', 'inputs/{0}.db|inputs/{0}-db.cfacts'.format(settings['dataset']),
        '--prog','inputs/{0}.ppr'.format(settings['dataset']), '--proppr',
        '--train','inputs/{0}-train.dset|inputs/{0}-train.exam'.format(settings['dataset']),
        '--test', 'inputs/eval.dset|inputs/eval.exam'])
    learner = setup(optdict,settings)

    # configute the experiment
    params = {'prog':optdict['prog'],
              'trainData':optdict['trainData'], 
              'testData':optdict['testData'],
              'targetMode':None,
              'savedTestPredictions':'tmp-cache/%s-eval.solutions.txt' % settings['dataset'],
              'savedTrainExamples':'tmp-cache/%s-train.examples' % settings['dataset'],
              'savedTestExamples':'tmp-cache/%s-eval.examples' % settings['dataset'],
              'learner':learner,
              'savedModel':'tmp-cache/%s-trained.db' % settings['dataset']
    }

    # run the experiment
    expt.Expt(params).run()
    
    
