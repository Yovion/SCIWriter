######Video source: https://ke.biowolf.cn
######??????ѧ??: https://www.biowolf.cn/
######΢?Ź??ںţ?biowolf_cn
######???????䣺2749657388@qq.com
######????΢??: 18520221056

#install.packages('survival')

library(survival)
pFilter=0.05                                                      #?????Թ??˱?׼
setwd("~/Bio/07_18_HNSC喉癌/model")       #???ù???Ŀ¼
st <- read.table("sur_expr_allmRNA.txt",header=T,sep="\t",check.names=F,row.names=1) 
# gene <- read.table("diffSig.xls")
# gene <- gene[abs(gene$logFC) > 3,]
gene <- read.table("dandaixie.txt",header=T) 
# rt <- rt[,c("futime","fustat",intersect(gene$x,colnames(rt)))]
diff <- read.table("diffSig.xls",header = T)
diff <- rownames_to_column(diff,var = "id")
a = 2
if(a == 1){
  upgene <- intersect(gene$id,diff$id)
  rt <- st[,c("futime","fustat",upgene)]
}else if(a == 2){
  rt <- st[,c("futime","fustat",intersect(gene$id,colnames(st)))]
}
# rt <- rt[,colnames(rt) != "MUC19"]
rt[,3:ncol(rt)] <- log2(rt[,3:ncol(rt)]+0.01)



outTab=data.frame()
sigGenes=c("futime","fustat")
#rt[,3:ncol(rt)]=log2(rt[,3:ncol(rt)]+0.01)
for(i in colnames(rt[,3:ncol(rt)])){
 cox <- coxph(Surv(futime, fustat) ~ rt[,i], data = rt)
 coxSummary = summary(cox)
 coxP=coxSummary$coefficients[,"Pr(>|z|)"]
 if(coxP<pFilter){
     sigGenes=c(sigGenes,i)
		 outTab=rbind(outTab,
		              cbind(id=i,
		              HR=coxSummary$conf.int[,"exp(coef)"],
		              HR.95L=coxSummary$conf.int[,"lower .95"],
		              HR.95H=coxSummary$conf.int[,"upper .95"],
		              pvalue=coxSummary$coefficients[,"Pr(>|z|)"])
		              )
  }
}
write.table(outTab,file="uniCox.txt",sep="\t",row.names=F,quote=F)
