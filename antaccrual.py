'''

antaccrual.py

Anticipated vs Actual Accrual in GU Cancer Trials

Question: how does the logged anticipated accrual compare to actual accrual in completed GU cancer trials?
	Secondary: how does this affect premature termination?

Why does it matter?
	predicting poorly accruing trials, or trial sites, could help plan for trials and avoid enrolling patients on trials
	that are doomed to fail

How will you do it?
	download completed trial info from clinicaltrials.gov
	automate extraction of anticipated accrual from clinicaltrials.gov archives

Why is this novel?
	clinicaltrials.gov (and the AACT database) only has a single entry for accrual (EITHER anticipated OR actual)
	this project will look at BOTH anticipated (from a prior registered trial log) AND actual accrual

How will this help?
	this will highlight how poor accrual is and emphasize importance of recruitment
	this method may be useful to future investigations and/or tools using clinicaltrials.gov
	knowledge of goal vs actual accrual may be helpful knowledge for trial planners

'''

### boilerplate code and functions
import re, urllib2, os, csv
from bs4 import BeautifulSoup

# function takes the NCT ID and returns a list of URLs for the change pages. returns a list of URLs
def archfind(nct):
	#print 'Just referenced archfind with nct %r.' % (nct[:-4])
	try:
		ncturl = 'http://clinicaltrials.gov/ct2/history/' + nct[:-4]
		nctarchopen = urllib2.urlopen(ncturl)
		nt = nctarchopen.read()

		changelocs = [m.start() for m in re.finditer('headers="VersionNumber"', nt)]
		changeurls = []
		for each_version in range(1,len(changelocs)+1):
			changeurls.append('http://clinicaltrials.gov/ct2/history/' + nct[:-4] + '?V_' + str(each_version))
		return changeurls

	except:
		#logging.exception('Exception within archfind.')
		return ['BROKENLINK']

# function checks if passed arg is a number. returns boolean
def is_num(s):
	try:
		float(s)
		return True
	except ValueError:
		return False

# function returns THE FIRST number found in a line after replacing html < > tags. returns integer
def findnum(line):
	### consider raising an error / suggesting a different line if there are multiple numbers
	#logging.debug("Within findnum function")
	sline = line.replace("<", " ").replace(">", " ")
	linelist =  [int(s) for s in sline.split() if s.isdigit()]
	#logging.debug("within findnum function right after linelist")

	if len(linelist) > 1:
		return 'morethan1num'
	elif len(linelist) == 1:
		return linelist[0]
	else:
		return 'noNumFound'

# the enrollment on the new clinicaltrials.gov archive site is always 2 lines ahead of enrollment
# because of the table format.
# function looks for the number that is 2 lines ahead of the first instance of "enrollment"
# then returns that number, and if it's anticipated or actual
def find_enrollment(nct_html):
	nt = nct_html.readlines()
	n=0
	for line in nt:
		# had to include > so that using text enrollment didn't cut early
		if ">Enrollment" in line:
			#print line
			#print n
			break
		else:
			n += 1

	# pull out the line containing enrollment
	enr_line_text = nt[n+2]
	# split the line on space and take just the number (first position in list)
	enrollment = enr_line_text.split(" ")[0]
	# split the line on space and take the second list position, then drop the brackets for enrollment type
	enrollment_type = enr_line_text.split(" ")[1][1:-1]

	return (enrollment, enrollment_type)


# find anticipated accrual. takes nctid. returns (anticipated accrual, actual accrual)
def find_ant(nctid):
	anticipated_accrual = "missing"
	actual_accrual = "missing"

	#print "referencing archfind"
	urllist = archfind(nctid)
	#print "starting loop"
	for each_site in urllist:
		#print "opening archive site"
		nct_html = urllib2.urlopen(each_site)
		#print "searching for enrollment line"
		(enrollment, enrollment_type) = find_enrollment(nct_html)

		if enrollment_type == "Anticipated" and anticipated_accrual == "missing":
			first_anticipated_accrual = enrollment
		elif enrollment_type == "Anticipated":
			last_anticipated_accrual = enrollment
		elif enrollment_type == "Actual":
			actual_accrual = enrollment

	return (first_anticipated_accrual, last_anticipated_accrual, actual_accrual)

# extracts list of NCT IDs from file folder containing all the xml files downloaded from clinicaltrials.gov
def extract_trials_list(cancer_type):
	# eventually, go to clinicaltrials.gov and download all trial files of a selected cancer type
	# these trials should only be those that are active
	# skipping this for now in favor of the other algorithms
	print 'Extracting trial list for %r.' % cancer_type
	ncts = []
	for root, dirs, fileList in os.walk(cancer_type + '_trials'):
		for fname in fileList:
			ncts.append(fname)
	included_trials = []
	for nct in ncts:
		included_trials.append(nct)

	return included_trials


### define included cancers
included_cancers = ['bladder', 'prostate', 'kidney', 'testicular', 'ureter', 'penile']
### to scale to other conditions, make a dict of lists
nct_lists = {}


### extract list of clinical trials for included
for each_cancer in included_cancers:
	nct_lists[each_cancer] = extract_trials_list(each_cancer)

### now build databases for each cancer type with anticipated and actual accrual
accrual_dicts = {}
for each_cancer in included_cancers:
	x = 0
	accrual_dicts[each_cancer] = []
	for each_nct in nct_lists[each_cancer]:
		x += 1
		try:
			(first_anticipated_accrual, last_anticipated_accrual, actual_accrual) = find_ant(each_nct)
			accrual_dicts[each_cancer].append((each_nct, first_anticipated_accrual, last_anticipated_accrual, actual_accrual, each_cancer))
		except:
			accrual_dicts[each_cancer].append((each_nct, "script failed", "script failed", "script failed"))
		print "Have referenced a total of %r out of %r trials." % (x, len(nct_lists[each_cancer]))

	print accrual_dicts[each_cancer]

	with open(each_cancer + 'accrual.csv', 'w') as outfile:
		accrual_writer = csv.writer(outfile, delimiter=',')
		accrual_writer.writerow(['nctid', 'first_anticipated', 'last_anticipated', 'actual', 'cancer_type'])
		for each_tuple in accrual_dicts[each_cancer]:
			accrual_writer.writerow(each_tuple)
