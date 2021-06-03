## Scalability Evaluation

This directory is dedicated to recreating the following analyses in our paper:

### 1. Scalability analysis in Sections 4.1 and 4.2.
The goal of this analysis is to compare the maximize attainable network size of different topologies (static and reconfigurable) when built using Electrical Packet Switches (EPS) and Optical Circuit Switches (OCS) of given radices. The topology classes used for this analyses are:

1) (Static) Fat tree
2) (Static) Expander
3) (Reconfigurable) ToR-reconfigurable Network (TRN)
4) (Reconfigurable) Pod-reconfigurable Network (PRN)

#### Instructions
* To recreate the scalability analysis, run `python scale_analysis.py`.

### 2. Path capacity analysis in Section 6.1.
In this analysis, we study the total path capacity distribution between two randomly-chosen end-points given any arbitrary OCS configuration. This highlights the difference in network capacity provided by different reconfigurable network models.

#### Instructions
* To recreate the path capacity, run `python path_capacity_dist.py`.

