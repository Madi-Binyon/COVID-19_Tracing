import random
import os
import threading
import time

# Input :
# Amount of people to simulate : INT
# Interaction amount per day   : INT (MAX AMOUNT OF PEOPLE - 1)
# Covid spread rate (Percent)  : 0-1
# Percent of people with app   : 0-1
#
# Ouput:
# Percentage of population with Covid-19 after X amount of days


# Ouput results to this file:
filename = "/results.txt"
# Simulation Parameters:
PopulationSize= 10000
InteractionAmount= 5
SpreadRate= 0.01
CovidPercentStart= 0.05

class Simulation:

    def __init__(self,  PopulationSize: int,
                        InteractionAmount: int,
                        SpreadRate: float,
                        AppPercentUsage: float,
                        CovidPercentStart: float
                        ):
        # Object Variables
        self.PopulationSize = PopulationSize                # Starting population size
        self.InteractionAmount = InteractionAmount          # Number of people per day that everybody interacts with (Random interaction)
        self.SpreadRate = SpreadRate                        # DEFAULT 1 PERCENT. Covid-19 Spread rate (Percent change of getting Covid-19 from interacting to a person with Covid-19)
        self.AppPercentUsage = AppPercentUsage                            # Percent of the population that use the WA Covid-19 contact
                                                            # tracing APP (Assumes they quaratine after app notifies them of exposure)
        self.CovidPercentStart = CovidPercentStart          # Percent of the population with Covid-19 on day 0

        # Simulation Variables
        self.MainPopulation = []                            # Maps population to list of people they have interacted with
        self.HasCovid = []                                  # All people who currently have Covid-19 and are not in quarantine (Spreaders)
                                                            # List contains list = [ID, SPREAD TIME (DAYS) = 2-14 no app or 2 if app] every day number is reduced then they are put in immune list
        self.Quarantine = []                                # People in quarantine (Can't interact or spread virus)
        self.Immune = [False] * self.PopulationSize         # Assuming people who have had Covid-19 are immune to getting it again
        self.HasApp = [False] * self.PopulationSize         # People who have WA Covid contact tracing app
        self.TotalInfected = 0
        # ID lists to update every day
        self.QuarantineIDList = []
        self.covidPosIDList = []
        self.NewlyInfected = []

        self.initialInfectionRate = None

        # Initialize main population map to a list which will be used for daily interactions
        for i in range(self.PopulationSize):
            self.MainPopulation.append([])
            
            # Randomly assigns people who have the app
            if random.randint(0, 100) <= (self.AppPercentUsage * 100):
                self.HasApp[i] = True

            # Randomly gives people Covid-19
            if random.randint(0, 100) <= (self.CovidPercentStart * 100):
                self.TotalInfected += 1
                if self.HasApp[i]:
                    self.HasCovid.append([i, 2])
                else:
                    self.HasCovid.append([i, random.randint(2,14)])
        
        # Initialize starting infection rate (Can't be given CovidPercentStart because of randomness)
        self.initialInfectionRate = len(self.HasCovid) / self.PopulationSize



    # Run simulation for given amount of days and returns percentage of popluation with Covid-19.
    def RunSimulation(self, Days: int):
        # Main Simulation Loop
        for _ in range(Days):
            print("\nDAY: ", _)
            print("Total People Infected: " + str(len(self.HasCovid)))
            print("Percent of Population Currently Infected: " + str(100 * (len(self.HasCovid) / self.PopulationSize)))
            # Update list of IDs to be used during simulation
            self.GetIDLists()

            # Interact then spread covid to interactions with 1 percent chance of spreading it
            self.Interact()

            # Check how many days people have had Covid. If they are at day 0 and have app make interactions
            # quarantine. Then add all to immune list. If person has app and being told to quaratine and they
            # have covid move them to immune list.
            self.CovidCheckAlert()

            # Subtract days from Quarantine and HasCovid
            self.SimUTIL()

        endingCovidInfectionRate = len(self.HasCovid) / self.PopulationSize
        return [self.initialInfectionRate, endingCovidInfectionRate, self.TotalInfected / self.PopulationSize]

    # Goes through every person and randomly interacts and spreads covid with the rest of the population.
    def Interact(self):
        # People are interactions for 14 days. So max list size will be self.InteractionAmount * 14.
        for person in range(self.PopulationSize):
            # Interact with self.InteractionAmount amount of people
            if person not in self.QuarantineIDList:
                for _ in range(self.InteractionAmount):
                    interaction = self.GetValidInteraction(person)
                    if interaction != -1:
                        # Adds an interaction to both the person and interaction
                        self.MainPopulation[person].append(interaction)
                        self.MainPopulation[interaction].append(person)

                        # Possibly get covid
                        self.GiveCovid(person, interaction)

            interactionList = self.MainPopulation[person]
            # Remove interactions older than 14 days
            if len(interactionList) > (self.InteractionAmount * 14):
                self.MainPopulation[person].clear()
                self.MainPopulation[person].extend(interactionList[(-1 * self.InteractionAmount * 14):])

    # 1 percent chance an interaction spreads covid between the two given people (As long as one is Covid-19 positive)
    def GiveCovid(self, person, interaction):
        if person in self.covidPosIDList and interaction not in self.NewlyInfected:
            if interaction not in self.covidPosIDList and not self.Immune[interaction] and interaction not in self.QuarantineIDList:
                # (DEFAULT 1 PERCENT) chance covid spreads
                if random.randint(0, 100) <= (self.SpreadRate * 100):
                    self.TotalInfected += 1
                    self.NewlyInfected.append(interaction)
        elif interaction in self.covidPosIDList and person not in self.NewlyInfected:
            if person not in self.covidPosIDList and not self.Immune[person] and person not in self.QuarantineIDList:
                # (DEFAULT 1 PERCENT) chance covid spreads
                if random.randint(0, 100) <= (self.SpreadRate * 100):
                    self.TotalInfected += 1
                    self.NewlyInfected.append(person) 

    # Returns valid ID(person) that given ID(person) can interact with
    def GetValidInteraction(self, ID):
        # Attempts one interaction. If it fails it returns a -1.
        # Attempting another interaction slows down the simulation by a lot, so it was removed.
        RandomNum = random.randint(0, self.PopulationSize - 1)
        if RandomNum != ID and RandomNum not in self.MainPopulation[ID] and RandomNum not in self.QuarantineIDList:
            return RandomNum
        return -1

    # Checks for people on day 0 of Covid and who have the app. Quarantine all interactions if they have app.
    # People who currently have covid and are an interaction will go immeditately to immune list instead of quarantine
    def CovidCheckAlert(self):
        covidDay0IDs = []
        for i in self.HasCovid:
            if i[1] <= 0 and self.HasApp[i[0]]:
                covidDay0IDs.append(i[0])
        # Goes through all people who have covid with the app and puts interactions in quarantine
        # NOTE: People who would be put in quarantine and already have covid will be put in immune list instead
        for person in covidDay0IDs:
            for interaction in self.MainPopulation[person]:
                if self.HasApp[interaction] and not self.Immune[interaction] and interaction not in self.QuarantineIDList:
                    # If interaction already has covid put into immune list else put in quarantine for 14 days.
                    if interaction in self.covidPosIDList:
                        self.Immune[interaction] = True
                        #Remove from covid list
                        for interaction2 in self.HasCovid:
                            if interaction2[0] == interaction:
                                self.HasCovid.remove([interaction, interaction2[1]])
                                break
                    else:
                        self.Quarantine.append([interaction, 14])
     
    # Subtract days UTIL if. People in Covid list will go to immune list
    def SimUTIL(self):
        # Subtracts 1 day from both covid list and quarantine list
        for person in self.HasCovid:
            if person[1] == 0:
                self.HasCovid.remove(person)
                self.Immune[person[0]] = True
            else:
                person[1] = person[1] - 1
        for person in self.Quarantine:
            if person[1] == 0:
                self.Quarantine.remove(person)
            else:
                person[1] = person[1] - 1

        # Add newly infected people
        for person in self.NewlyInfected:
            if self.HasApp[person]:
                self.HasCovid.append([person, 2])
            else:
                self.HasCovid.append([person, random.randint(2,14)])
        self.NewlyInfected.clear()
        
    # Gets the ID's of all the people in quarantine and who are Covid-19 Positive.
    def GetIDLists(self):
        self.QuarantineIDList = [x[0] for x in self.Quarantine]
        self.covidPosIDList = [x[0] for x in self.HasCovid]

# Main function to call for a simulation (Can call from a thread for multi-threading)
def simUtil(appusage):
    global filename
    global PopulationSize
    global InteractionAmount
    global SpreadRate
    global CovidPercentStart
    AppPercentUsage= appusage
    time0 = time.time()

    sim1 = Simulation(
        PopulationSize= PopulationSize,
        InteractionAmount= InteractionAmount,
        SpreadRate= SpreadRate,
        AppPercentUsage= AppPercentUsage,
        CovidPercentStart= CovidPercentStart)
    SimDays = 100

    out = sim1.RunSimulation(SimDays)
    # File Output
    output = "{PopulationSize}\t{InteractionAmount}\t{SpreadRate:.2f}\t{StartInfection:.2f}\t{EndInfection:.2f}\t{TotalInfected:.2f}\t{AppUsage:.2f}\n"
    output = output.format(PopulationSize= PopulationSize, InteractionAmount= InteractionAmount, SpreadRate= (100 * SpreadRate), StartInfection= (100 * out[0]), EndInfection= (100 * out[1]), TotalInfected= (100 * out[2]), AppUsage= (100 * AppPercentUsage))
    print("\n\nRESULTS:\nPopulation: " + str(PopulationSize) + "\nInteraction Amount: " + str(InteractionAmount) + "\nSpread Rate: " + str(SpreadRate * 100) + "\nStarting Infection Percentage: " + str(100 * out[0]) + "\nEnding Infection Rate: " + str(100 * out[1]) + "\nTotal Percent Of Population Infected: " + str(100 * out[2]) + "\nApp Usage Percentage: " + str(100 * AppPercentUsage) + "\n")
    
    dir_path = os.path.dirname(__file__)
    filewrite = open(str(dir_path) + filename, 'a')
    filewrite.write(str(output))
    #Times how long sim took
    time1 = time.time()
    print(AppPercentUsage, ": TIME:", time1 - time0)

def main():
    global filename
    Heading = "PopulationSize" + " | " + "InteractionAmount" + " | " + "SpreadRate" + " | " + "Starting Infection Percentage" + " | " + "Ending Infection Rate" + " | " + "Total Percent of Population Infected" + " | " + "AppPercentUsage" + "\n"
    dir_path = os.path.dirname(__file__)
    filewrite = open(str(dir_path) + filename, 'a')
    filewrite.write(str(Heading))
    filewrite.close()

    t0 = threading.Thread(target=simUtil, args=(0.00,))
    t0.start()
    t0.join()
    '''
    t1 = threading.Thread(target=simUtil, args=(0.05,))
    t2 = threading.Thread(target=simUtil, args=(0.10,))
    t3 = threading.Thread(target=simUtil, args=(0.15,))
    t4 = threading.Thread(target=simUtil, args=(0.20,))
    t5 = threading.Thread(target=simUtil, args=(0.25,))
    t6 = threading.Thread(target=simUtil, args=(0.30,))
    t7 = threading.Thread(target=simUtil, args=(0.35,))
    t8 = threading.Thread(target=simUtil, args=(0.40,))
    t9 = threading.Thread(target=simUtil, args=(0.45,))
    t10 = threading.Thread(target=simUtil, args=(0.50,))
    t11 = threading.Thread(target=simUtil, args=(0.55,))
    t12 = threading.Thread(target=simUtil, args=(0.60,))
    t13 = threading.Thread(target=simUtil, args=(0.65,))
    t14 = threading.Thread(target=simUtil, args=(0.70,))
    t15 = threading.Thread(target=simUtil, args=(0.75,))
    t16 = threading.Thread(target=simUtil, args=(0.80,))
    t17 = threading.Thread(target=simUtil, args=(0.85,))
    t18 = threading.Thread(target=simUtil, args=(0.90,))
    t19 = threading.Thread(target=simUtil, args=(0.95,))
    t20 = threading.Thread(target=simUtil, args=(1.00,))

    t0.start()
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    t6.start()
    t7.start()
    t8.start()
    t9.start()
    t10.start()
    t11.start()
    t12.start()
    t13.start()
    t14.start()
    t15.start()
    t16.start()
    t17.start()
    t18.start()
    t19.start()
    t20.start()

    t0.join()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    t5.join()
    t6.join()
    t7.join()
    t8.join()
    t9.join()
    t10.join()
    t11.join()
    t12.join()
    t13.join()
    t14.join()
    t15.join()
    t16.join()
    t17.join()
    t18.join()
    t19.join()
    t20.join()
    '''
if __name__== "__main__":
  main()