const Joi = require('joi');
const express = require('express');
const request = require('request');
const ejs = require('ejs');
const bodyParser = require('body-parser');
const multer = require('multer');
const debug = require('debug')('myapp:server');
const path = require('path');
const app = express();

var storage = multer.diskStorage({
  destination: (req, file, cb) => {
      cb(null, './public/uploads')
  },
  filename: (req, file, cb) => {
      cb(null, file.fieldname + '-' + Date.now() + path.extname(file.originalname))
  },
  fileFilter: function(req, file, next){
    if(!file){
      next();
    }
    const pdf = file.mimetype.startsWith('application/pdf');
    if(pdf){
      next(null, true);
    }else{
      return next();
    }
  }
});


const upload = multer({ storage: storage });

app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs')
app.use(express.json());
app.use(express.static('public'));


app.get('/compare', (req, res) => {
  res.render('compare', {error: null});
});

app.get('/ebill', (req, res) => {
  res.render('ebill', {error: null});
});

app.post('/ebill', upload.single('file'), function(req,res) {
  ext = req.file.path.split(".");
  if (ext[ext.length-1].toLowerCase() === "pdf") {
    debug(req.file);
    dir = path.resolve("./") +"/"+ req.file.path;
    var url = `http://localhost:8800/getbilldata?dir=${dir}`;
    request(url, function (err, response, body) {
      if (err != null){
        res.render('ebill', {error: 'Connection to server failed'});
        return;
      }
      try{
        const result = JSON.parse(body);
        const newres = {
          "postcode": result['postcode'],
          "estimate": result['estimate'],
          "plan": dissect(result['plan'], result['company'])
        }
        res.render('ebillresult', {result: newres, error: null});
      } catch(err){
        res.render('ebillresult', {result: null, error:{"error": "An error has occured"}})
      }
    });
  } else {
    return res.send()
  }
})

app.get('/', (req, res) => {
  res.render('index');
});

app.get('/postcode', (req, res) => {
  res.render('postcode', {query: null, subresults:null, results: null, best:null, error: null, checkedR: "main"});
});

app.post('/postcode', function (req, res) {
  const qchoice = req.body.type;
  var query = "";
  query = req.body.query;
  if (qchoice == 'main'){
    var url = `http://localhost:8800/getmainplans?postcode=${query}`;
    request(url, function (err, response, body) {
      if (err != null){
        res.render('postcode', {query: query, subresults:null, results: null, best:null, error: 'Connection to server failed', checkedR: qchoice});
        return;
      }
      const results = JSON.parse(body);
      var plans = [];
      var bestPlans = [];
      if ( (typeof results.allPlans) !== 'undefined' && results.allPlans.length > 0) {
          for (var i in results.allPlans) {
            var plan = results.allPlans[i];
            var company = plan.company;
            var cost = '$'+plan.cost;
            var discount = plan.discount+"%";
            var distributor = plan.distributor;
            var name = plan.name;
            var pricePerkWh = plan.pricePerkWh;
            var usage = plan.usage;
            plans.push({name: name, company: company, cost: cost, pricePerkWh: pricePerkWh, discount: discount, distributor: distributor, usage: usage});
          }
          plan = results.cheapestPerCostPlan;
          var company = plan.company;
          var cost = '$'+plan.cost;
          var discount = plan.discount+"%";
          var distributor = plan.distributor;
          var name = plan.name;
          var pricePerkWh = plan.pricePerkWh;
          var usage = plan.usage;
          bestPlans.push({feature: "Lowest price", name: name, company: company, cost: cost, pricePerkWh: pricePerkWh, discount: discount, distributor: distributor, usage: usage});
          plan = results.cheapestPerkWhPlan;
          var company = plan.company;
          var cost = '$'+plan.cost;
          var discount = plan.discount+"%";
          var distributor = plan.distributor;
          var name = plan.name;
          var pricePerkWh = plan.pricePerkWh;
          var usage = plan.usage;
          bestPlans.push({feature: "Cheapest kWh", name: name, company: company, cost: cost, pricePerkWh: pricePerkWh, discount: discount, distributor: distributor, usage: usage});
          res.render('postcode', {query: query, subresults:null, results: plans, best: bestPlans, error: null, checkedR: qchoice});
          return;
      } else {
        
        if ((typeof results.error) !== 'undefined'){
          res.render('postcode', {query: query, subresults:null, results: null, best:null, error: results.error, checkedR: qchoice});
        }
        else{
          res.render('postcode', {query: query, subresults:null, results: null, best:null, error: "No results found", checkedR: qchoice});
        }
        return;
      }
    });
  }
  else if (qchoice == 'sub'){
    var url = `http://localhost:8800/getsubplans?postcode=${query}`;
    request(url, function (err, response, body) {
      if (err != null){
        res.render('postcode', {query: query, subresults:null, results: null, best:null, error: 'Connection to server failed', checkedR: qchoice});
        return;
      }
      const results = JSON.parse(body);
      var plans = [];
      if (results) {
        var companies = ["Dodo", "EnergyAustralia", "OriginEnergy", "AGL"];
        for (var i in companies){
          for (var plan in results[companies[i]]){
            plan = results[companies[i]][plan]
            var id = plan.ID;
            var title = plan.title;
            var additionalDetails = plan.additionalDetails;
            if (additionalDetails){
              var billingandPriceDetails = additionalDetails.billingandPriceDetails;
              for (var j in billingandPriceDetails){
                currentDetails = billingandPriceDetails[j]
                if (currentDetails.paymentOptions){
                  var paymentOptions = currentDetails.paymentOptions;
                }
                if (currentDetails.otherDetails){
                  var otherDetails = currentDetails.otherDetails;
                  var otherDetailsStr = "";
                    for (var j in otherDetails){
                      c = otherDetails[j]
                      otherDetailsStr += (parseInt(j)+1).toString()+ "- " + c + "\\n";
                    }
                } else {
                  otherDetailsStr = "N/A";
                }
                if (currentDetails.billingPeriod){
                  var billingPeriod = currentDetails.billingPeriod;
                }
              }

              var contractDetails = additionalDetails.contractDetails;
              var distributor = null
              var contractDetailsStr = "";
              if (contractDetails){
                for (var j in contractDetails){
                  currentContract = contractDetails[j];
                  contractDetailsStr += (parseInt(j)+1).toString()+ "- " + currentContract.title +": "+currentContract.description+"\\n";
                  details = contractDetails[j]
                  if (details['title'] == 'Distributor'){
                    distributor = details['description']
                  }
                }
              } else {
                distributor = "Unknown";
                contractDetailsStr = "N/A";
              }
              var termsandConditions = additionalDetails.termsandConditions;
              var termsandConditionsStr = "";
              if (termsandConditions){
                for (var j in termsandConditions.details){
                  c = termsandConditions.details[j]
                  termsandConditionsStr += (parseInt(j)+1).toString()+ "- " + c + "\\n";
                }
              } else {
                termsandConditionsStr = "N/A";
              }
              var discounts = plan.discounts;
              var discountsStr = "";
              if (discounts){
                for (var j in discounts.discounts){
                  discount = discounts.discounts[j];
                  discountsStr += (parseInt(j)+1).toString()+ "- " +discount.title + ": " + discount.value+discount.type+"\\n";
                }
                if (discounts.note){
                  discountsStr += "\\nNote: "+discounts.note;
                }
              } else{
                discountsStr = "N/A";
              }
              var eligiblity = plan.eligiblity;
              var eligiblityStr = "";
              if (eligiblity.length){
                for (var j in eligiblity){
                  point = eligiblity[j];
                  eligiblityStr += (parseInt(j)+1).toString()+ "- " +point.title + point.description +"\\n";
                }
              } else{
                eligiblityStr = "N/A";
              }
              var features = plan.features;
              var featuresStr = "";
              if (features){
                for (var j in features){
                  featuresStr+= (parseInt(j)+1).toString()+ "- " +features[j]+"\\n";
                }
              } else {
                featuresStr = "N/A";
              }
              var feesandCharges = plan.feesandCharges;
              var feesandChargesStr = "";
              if (feesandCharges){
                for (var j in feesandCharges){
                  feeorcharge = feesandCharges[j];
                  feesandChargesStr += (parseInt(j)+1).toString() +"- "+ feeorcharge.title + ": \\n     " + feeorcharge.description + "\\n     Amount: ";
                  if (feeorcharge.type == "%"){
                    feesandChargesStr += feeorcharge.amount + feeorcharge.type+"\\n";
                  }
                  else if (feeorcharge.type == "$"){
                    feesandChargesStr += feeorcharge.type + feeorcharge.amount+"\\n";
                  }
                }
              } else {
                feesandChargesStr = "N/A";
              }
              var greenpower = plan.greenpower;
              var greenpowerStr = "";
              if (greenpower){
                for (var j in greenpower){
                  c = greenpower[j];
                  greenpowerStr += (parseInt(j)+1).toString() +"- "+ c.description + "\\n     Usage: " + c.usage +" for: " + c.charge +'\\n';  
                }
              } else {
                greenpowerStr = "N/A";
              }
              var priceSummary = plan.priceSummary;
              if (priceSummary){
                if (priceSummary.controlledLoad){
                  var controlledLoad = priceSummary.controlledLoad[0];
                }
                var generalCharges = priceSummary.generalCharges;
                var timeofUseCharges = priceSummary.timeOfUseCharges;
              }
              var timeofUseChargesStr = "";
              if (timeofUseCharges.length){
                for (var j in timeofUseCharges){
                  c = timeofUseCharges[j];
                  timeofUseChargesStr += "*- For: "+ c.season + ", Spanning: " + c.period +", During: "+ c.weekdays +'\\n';
                  for (var k in c.details){
                    ck = c.details[k];
                    timeofUseChargesStr += "   " + (parseInt(k)+1).toString() +"- Starting at: "+ ck.startFromHrs + " Until: " +ck.endAtHrs +"\\n     Is classified as: " + ck.usageType + ", and costs: " + ck.price +" "+ ck.type + "\\n";
                  }  
                }
              } else {
                timeofUseChargesStr = "N/A";
              }
              var solar = plan.solar;
              var solarStr = "";
              if (solar){
                for (var j in solar){
                  c = solar[j];
                  solarStr += (parseInt(j)+1).toString() +"- "+ c.description + "\\n     Payback: " + c.value +" "+ c.type +'\\n';  
                }
              } else{
                solarStr = "N/A";
              }
              var tariffs = plan.tariffs;
              var company = null
              if (companies[i] == "EnergyAustralia"){
                company = "Energy Australia";
              }
              else if (companies[i] == "OriginEnergy"){
                company = "Origin Energy";
              }
              else{
                company = companies[i]
              }
              plans.push({company: company, id: id, title: title, billingPeriod: billingPeriod, paymentOptions: paymentOptions, otherDetails: otherDetails, otherDetailsStr: otherDetailsStr, distributor: distributor, 
                contractDetails: contractDetails, contractDetailsStr: contractDetailsStr, termsandConditions: termsandConditions, termsandConditionsStr: termsandConditionsStr, discounts: discounts, 
                discountsStr: discountsStr, eligiblity: eligiblity, eligiblityStr: eligiblityStr, features: features, featuresStr: featuresStr, feesandCharges: feesandCharges, feesandChargesStr:feesandChargesStr, 
                greenpower: greenpower, greenpowerStr: greenpowerStr,controlledLoad: controlledLoad, generalCharges: generalCharges, timeofUseCharges: timeofUseCharges, timeofUseChargesStr: timeofUseChargesStr, 
                solar: solar, solarStr: solarStr, tariffs: tariffs})
            }
          }
        }
        res.render('postcode', {query: query, subresults: plans, results: null, best:null, error: null, checkedR: qchoice});
        return;
      }
    });
  } else {
    res.render('postcode', {query: query, subresults:null, results: null, best:null, error: 'Corrupt request', checkedR: qchoice});
    return;
  }
});



const port = process.env.PORT || 3000;

app.listen(port, () => console.log(`Listening on port ${port}...`));


function dissect(plan, company){
  var id = plan.ID;
  var title = plan.title;
  var additionalDetails = plan.additionalDetails;
  if (additionalDetails){
    var billingandPriceDetails = additionalDetails.billingandPriceDetails;
    for (var j in billingandPriceDetails){
      currentDetails = billingandPriceDetails[j]
      if (currentDetails.paymentOptions){
        var paymentOptions = currentDetails.paymentOptions;
      }
      if (currentDetails.otherDetails){
        var otherDetails = currentDetails.otherDetails;
        var otherDetailsStr = "";
          for (var j in otherDetails){
            c = otherDetails[j]
            otherDetailsStr += (parseInt(j)+1).toString()+ "- " + c + "\\n";
          }
      } else {
        otherDetailsStr = "N/A";
      }
      if (currentDetails.billingPeriod){
        var billingPeriod = currentDetails.billingPeriod;
      }
    }

    var contractDetails = additionalDetails.contractDetails;
    var distributor = null
    var contractDetailsStr = "";
    if (contractDetails){
      for (var j in contractDetails){
        currentContract = contractDetails[j];
        contractDetailsStr += (parseInt(j)+1).toString()+ "- " + currentContract.title +": "+currentContract.description+"\\n";
        details = contractDetails[j]
        if (details['title'] == 'Distributor'){
          distributor = details['description']
        }
      }
    } else {
      distributor = "Unknown";
      contractDetailsStr = "N/A";
    }
    var termsandConditions = additionalDetails.termsandConditions;
    var termsandConditionsStr = "";
    if (termsandConditions){
      for (var j in termsandConditions.details){
        c = termsandConditions.details[j]
        termsandConditionsStr += (parseInt(j)+1).toString()+ "- " + c + "\\n";
      }
    } else {
      termsandConditionsStr = "N/A";
    }
    var discounts = plan.discounts;
    var discountsStr = "";
    if (discounts){
      for (var j in discounts.discounts){
        discount = discounts.discounts[j];
        discountsStr += (parseInt(j)+1).toString()+ "- " +discount.title + ": " + discount.value+discount.type+"\\n";
      }
      if (discounts.note){
        discountsStr += "\\nNote: "+discounts.note;
      }
    } else{
      discountsStr = "N/A";
    }
    var eligiblity = plan.eligiblity;
    var eligiblityStr = "";
    if (eligiblity.length){
      for (var j in eligiblity){
        point = eligiblity[j];
        eligiblityStr += (parseInt(j)+1).toString()+ "- " +point.title + point.description +"\\n";
      }
    } else{
      eligiblityStr = "N/A";
    }
    var features = plan.features;
    var featuresStr = "";
    if (features){
      for (var j in features){
        featuresStr+= (parseInt(j)+1).toString()+ "- " +features[j]+"\\n";
      }
    } else {
      featuresStr = "N/A";
    }
    var feesandCharges = plan.feesandCharges;
    var feesandChargesStr = "";
    if (feesandCharges){
      for (var j in feesandCharges){
        feeorcharge = feesandCharges[j];
        feesandChargesStr += (parseInt(j)+1).toString() +"- "+ feeorcharge.title + ": \\n     " + feeorcharge.description + "\\n     Amount: ";
        if (feeorcharge.type == "%"){
          feesandChargesStr += feeorcharge.amount + feeorcharge.type+"\\n";
        }
        else if (feeorcharge.type == "$"){
          feesandChargesStr += feeorcharge.type + feeorcharge.amount+"\\n";
        }
      }
    } else {
      feesandChargesStr = "N/A";
    }
    var greenpower = plan.greenpower;
    var greenpowerStr = "";
    if (greenpower){
      for (var j in greenpower){
        c = greenpower[j];
        greenpowerStr += (parseInt(j)+1).toString() +"- "+ c.description + "\\n     Usage: " + c.usage +" for: " + c.charge +'\\n';  
      }
    } else {
      greenpowerStr = "N/A";
    }
    var priceSummary = plan.priceSummary;
    if (priceSummary){
      if (priceSummary.controlledLoad){
        var controlledLoad = priceSummary.controlledLoad[0];
      }
      var generalCharges = priceSummary.generalCharges;
      var timeofUseCharges = priceSummary.timeOfUseCharges;
    }
    var timeofUseChargesStr = "";
    if (timeofUseCharges.length){
      for (var j in timeofUseCharges){
        c = timeofUseCharges[j];
        timeofUseChargesStr += "*- For: "+ c.season + ", Spanning: " + c.period +", During: "+ c.weekdays +'\\n';
        for (var k in c.details){
          ck = c.details[k];
          timeofUseChargesStr += "   " + (parseInt(k)+1).toString() +"- Starting at: "+ ck.startFromHrs + " Until: " +ck.endAtHrs +"\\n     Is classified as: " + ck.usageType + ", and costs: " + ck.price +" "+ ck.type + "\\n";
        }  
      }
    } else {
      timeofUseChargesStr = "N/A";
    }
    var solar = plan.solar;
    var solarStr = "";
    if (solar){
      for (var j in solar){
        c = solar[j];
        solarStr += (parseInt(j)+1).toString() +"- "+ c.description + "\\n     Payback: " + c.value +" "+ c.type +'\\n';  
      }
    } else{
      solarStr = "N/A";
    }
    var tariffs = plan.tariffs;
    var company = company
    var x = {company: company, id: id, title: title, billingPeriod: billingPeriod, paymentOptions: paymentOptions, otherDetails: otherDetails, otherDetailsStr: otherDetailsStr, distributor: distributor, 
      contractDetails: contractDetails, contractDetailsStr: contractDetailsStr, termsandConditions: termsandConditions, termsandConditionsStr: termsandConditionsStr, discounts: discounts, 
      discountsStr: discountsStr, eligiblity: eligiblity, eligiblityStr: eligiblityStr, features: features, featuresStr: featuresStr, feesandCharges: feesandCharges, feesandChargesStr:feesandChargesStr, 
      greenpower: greenpower, greenpowerStr: greenpowerStr,controlledLoad: controlledLoad, generalCharges: generalCharges, timeofUseCharges: timeofUseCharges, timeofUseChargesStr: timeofUseChargesStr, 
      solar: solar, solarStr: solarStr, tariffs: tariffs};
    return x;
  }
}