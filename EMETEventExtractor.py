from BAM import soap_query, relevance_query
from datetime import timedelta
from time import clock
import json
import sys
import os

class events:

    username = ""
    password = ""
    server = ""
    output_path = ""
    log_path = ""
    filter = []
    returns = []
    webreports_events = []
    
    def __init__(self, new_user, new_pass, new_server, new_filter, new_returns, new_output_path):
        '''
        Assigns webreports credentials and filter value to global variables for later use.
        '''
        self.username = new_user
        self.password = new_pass
        self.server = new_server
        self.filter = new_filter
        self.returns = new_returns
        self.output_path = new_output_path

    def get_webreports_events(self):
        '''
        Pulls recent emet events from webreports based on filter.
        '''

        #Create Emet Return and Search properties
        #Optional EMET Timeframe Settings: Emet Triggered Mitigations for (2 hours, 30 days, a year)
        f.write("<get_webreports_events> : <expecting username and password to webreports> \n")
        search = "computers"

        #Create relevance query and fetch results
        f.write("<get_webreports_events> : <creating query> \n")
        query = relevance_query(self.returns, self.filter, search)
        f.write("<get_webreports_events> : <getting query results> \n")
        results = soap_query(self.username, self.password, self.server, query.Query)

        #Save webreports_events as dictionary
        end_time = clock()
        string = "<get_webreports_events> : <now saving into webreports_events and exiting. %s> \n" % (timedelta(seconds = end_time - start_time))
        f.write(string)
        self.webreports_events = self.webreports_parse(results)
		
        # Troubleshooting code to check BFWR!
        # webreports_results_file = open("webreports_return.txt", "w")
        # for line in results:
        #    webreports_results_file.write(line.encode("utf-8"))
        #    webreports_results_file.write("\n")
		
    def webreports_parse(self, results):
        '''
        Takes results from a query to webreports, and holds each result in a dictionary,
        then saves them all in a list format to the returned variable "answer".
        Expects a list of results.
        ''' 
        
        f.write("<webreports_parse> : <expecting results>\n")
        answer = []
        dict = {}
        
        f.write("<webreports_parse> : <now parsing results> \n")
        #Begin parsing into dictionary form
        for count in range(0, len(results)):
            new_events = results[count]
            # Find number of Emet values by bar count, and start parsing the EMET key/values
            num_properties = new_events.count("|")
            # Remove leading "(" and first comma in EMET TIME value
            
            if (new_events.find("TIME|") != -1):
                new_events = new_events.replace(",", "", 1).replace("( ", "", 1)
            else:
                new_events = new_events.replace("( ", "", 1)
            
            # Split by bars to get EMET key/values
            new_events = new_events.split("|")
            # Remove ending ")" in last emet property
            new_events[num_properties] = new_events[num_properties].replace(" )", "", 1)

            # Note non-emet properties and the final emet property are in the final element
            # of new_events, so we must split them by commas, and save them in a temporary list. 
            # Furthermore, we must clear this incorrect element from new_events.
            temp_list = new_events[num_properties].split(",", len(self.returns)-1)
            new_events.pop(num_properties)

            # Append the non-emet values and final emet value in temp_list to new_events
            for event in temp_list: 
                new_events.append(event)
            temp_list = []

            # Remove the ending comma in emet values
            for count in range(1, num_properties): 
                new_events[count] = new_events[count].rsplit(",", 1)

            # Now we have EMET events as list of a string, lists, and another string: 
            # (Assume there are n Key/Value pairs)
            # [ Key1, [Value1, Key2], [Value2, Key3], ...[Value n-1, Key n], Value n ]
            # Normalize into a dictionary of key value pairs
            
            for count in range(0, num_properties):
                if (count == 0):
                    # First Key/Value Pair ( Key 1, [Value 1, ... ] )
                    dict[new_events[count]] = new_events[count+1][0]
                elif (count == num_properties-1 ):
                    # Last Key/Value Pair ( [ ..., Key n ], Value n ] )
                    dict[new_events[num_properties-1][1]] = new_events[num_properties]
                else:
                    # All Key/Values in the middle ( [ ..., Key ], [ Value, ...] )
                    dict[new_events[count][1]] = new_events[count+1][0]
            
            # Create dicts out of the non-Emet properties and remove spaces in front of values 
            count = 1
            for return_property in self.returns[1:]:
                dict[return_property.replace(" ","_")] = new_events[num_properties+count][1:]
                count += 1

            # Replace commas in multiple IPs with semicolons to avoid comma parsing confusion 
            if (dict["ip_addresses"].find(")") != 0):
                dict["ip_addresses"] = dict["ip_addresses"].replace(",", ";")

            # Append the dictionary to the return list (answer) and clear the dict for the next event
            answer.append(dict.copy())
            dict.clear()

        end_time = clock()
        string = "<webreports_parse> : <Now returning answer and exiting. %s> \n" % (timedelta(seconds = end_time - start_time))
        f.write(string)
        self.webreports_events = answer
        return answer

    def push_events(self):
        '''
        Deduplicates and pushes events in webreports_events in key value pairs to a file.
        '''

        f.write("<push_events> : <Entering push_events function. Preparing to create event strings.> \n")
        # Get a list of string-ified key, value events
        webreports_events = []
        temp_string = ""
        for event in self.webreports_events:
			try:
				#Place time value in first position
				if "TIME" in event:
					temp_string += "TIME=%s, " % (event["TIME"])
					for key in event:
						if key != "TIME":
								temp_string += "%s=%s, " % (key.encode("utf-8"), event[key].encode("utf-8"))
					temp_string +="\n"
					webreports_events.append(temp_string)
					temp_string = ""
			except:
					f.write("<push_events> : <UnicodeEncodeError: Could not encode or decode character.> \n")
					f.write("<push_events> : <Event: %r.> \n" % event)
		
            
        
        # Deduplicate and order this list of events
        webreports_events = sorted(set(webreports_events))

        f.write("<push_events> : <Opening file and reading in previous events.> \n")
        # Pull a list of events from output file
        splunk_file = open(self.output_path, "a")
        splunk_file = open(self.output_path, "r")
        locally_cached_splunk_events = []
        for line in splunk_file:
            locally_cached_splunk_events.append(line)

        f.write("<push_events> : <Creating unique events and submitting into file.> \n")
        # Find the events not yet in the output file
        # Also cast list of file events to unicode so they can be compared with list of events
        for count in range(0, len(locally_cached_splunk_events)):
            locally_cached_splunk_events[count] = locally_cached_splunk_events[count].decode("utf-8")

        locally_cached_splunk_events = sorted(set(locally_cached_splunk_events))

        # Get unique webreports events that are not in splunk cache
        unique_events = []
        for event in webreports_events:
            if event not in locally_cached_splunk_events:
                unique_events.append(event)

        string = "<push_events> : <There are %s unique events that will be pushed to the \"Splunk Events\" file.> \n" % (len(unique_events))
        f.write(string)

        # Push unique_events
        for event in unique_events:
            event = event.encode("utf-8")
            splunk_file = open(self.output_path, "a", 0)
            splunk_file.write(event)
        end_time = clock()
        string = "<push_events> : <Exiting function. %s> \n" % (timedelta(seconds = end_time - start_time))
        f.write(string)
        
start_time = clock()

#Grab commandline argument for config filepath
#Detect Errors if no filepath found or, or if incorrect filepath
try:
    config_file =  sys.argv[1]
    try:
        open(config_file, "r")
    except IOError:
        print "No valid config filepath found."
except IOError:
        print "No config filepath argument found."

# Getting credentials from config file (JSON)
with open(config_file, "r") as data_file:
    data = json.load(data_file)
username = data["Settings"][0]["username"] 
password = data["Settings"][0]["password"] 
webreports_server = data["Settings"][0]["webreports_server"]
returns = data["Settings"][0]["returns"]
log_path = data["Settings"][0]["log_path"]
output_path = data["Settings"][0]["output_path"]
filters = data["Settings"][1]["filters"].values()

#Create Default ouput and log paths
if (log_path == ""):
	local_path = os.path.dirname(os.path.abspath(__file__))
	log_path = os.path.join(local_path, "EMETEventExtractorLogs.log")
if (output_path == ""):
	local_path = os.path.dirname(os.path.abspath(__file__))
	output_path = os.path.join(local_path, "EMET-Events.csv")

# Clearing and opening Logs
f = open(log_path, "w")
f = open(log_path, "a", 0)

### TESTING ###
my_event = events(username, password, webreports_server, filters, returns, output_path)
my_event.get_webreports_events()
my_event.push_events()

## FINISHING ##
end_time = clock()
string = "Now exiting. Program time was: %s" % (timedelta(seconds = end_time - start_time))
f.write(string)
